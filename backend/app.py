from flask import Flask, jsonify, request
from flask_cors import CORS
from services.file_handler import save_uploaded_file, MAX_FILE_SIZE
from services.zip_processor import extract_zip, get_code_files
from services.chunker import chunk_files
from services.vector_store import create_vector_store, load_vector_store
from services.llm_service import generate_architecture_analysis
import os
import logging
import re

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type"]}})
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
app.config['UPLOAD_FOLDER'] = 'uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

uploaded_files = []
current_extract_folder = None

def clean_file_path(file_path):
    if not file_path:
        return file_path
    
    path = file_path.replace('\\', '/')
    
    if path.startswith('extracted/'):
        path = path[10:]
    
    parts = path.split('/')
    
    if len(parts) >= 2 and parts[0] == parts[1]:
        parts = parts[1:]
    
    if len(parts) > 1 and parts[0] and (
        parts[0].endswith('-main') or 
        parts[0].endswith('-master') or
        parts[0].endswith('-dev')
    ):
        parts = parts[1:]
    
    return '/'.join(parts)

def get_file_list():
    if not current_extract_folder or not os.path.exists(current_extract_folder):
        return []
    
    files = []
    for root, _, filenames in os.walk(current_extract_folder):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, current_extract_folder)
            files.append(rel_path)
    return sorted(files)

def generate_file_tree():
    if not current_extract_folder or not os.path.exists(current_extract_folder):
        return "No files uploaded yet."
    
    tree_lines = []
    root_name = os.path.basename(current_extract_folder)
    tree_lines.append(f"{root_name}/")
    tree_lines.append("│")
    
    def build_tree(directory, prefix=""):
        try:
            items = sorted(os.listdir(directory))
            dirs = [item for item in items if os.path.isdir(os.path.join(directory, item))]
            files = [item for item in items if os.path.isfile(os.path.join(directory, item))]
            
            all_items = dirs + files
            
            for i, item in enumerate(all_items):
                is_last = (i == len(all_items) - 1)
                item_path = os.path.join(directory, item)
                
                if os.path.isdir(item_path):
                    connector = "└── " if is_last else "├── "
                    tree_lines.append(f"{prefix}{connector}{item}/")
                    
                    extension = "    " if is_last else "│   "
                    build_tree(item_path, prefix + extension)
                else:
                    connector = "└── " if is_last else "├── "
                    tree_lines.append(f"{prefix}{connector}{item}")
        except PermissionError:
            pass
    
    build_tree(current_extract_folder)
    return '\n'.join(tree_lines)

def extract_function_or_section(question):
    patterns = [
        r'\b(function|method|class)\s+([\w_]+)',
        r'\b([\w_]+)\s+(function|method|class)',
        r'\bthe\s+([\w_]+)\s+(function|method)',
        r'\b([\w_]+)\(\)',
        r'\bexplain\s+([\w_]+)\s+(function|method)',
        r'\b([\w_]+)\s+function\b',
        r'\bsection\s+([\w\s]+?)\b(?:do|work|mean)'
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            groups = match.groups()
            for group in groups:
                if group and group.lower() not in ['function', 'method', 'class', 'the']:
                    return group
    return None

def extract_file_path(question):
    patterns = [
        r'(?:code of|file|explain|show|summary of|summarize|content in|content of)\s+([\w\-]+\.[a-z]{1,5})\b',  # "content in README.md"
        r'\b(readme\.md)\b',  # Match README.md specifically
        r'([\w\-]+/[\w\-/.]+\.[a-z]{1,5})',
        r'([\w\-]+\\[\w\-\\.]+\.[a-z]{1,5})',
        r'\b([A-Z][\w\-]*\.[a-z]{2,5})\b'  # Match files starting with capital letter
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            return match.group(1).replace('\\', '/')
    return None

def find_file_in_repository(filename):
    if not current_extract_folder or not os.path.exists(current_extract_folder):
        return None
    
    filename = filename.replace('\\', '/').strip('/')
    
    exact_path = os.path.join(current_extract_folder, filename)
    if os.path.isfile(exact_path):
        return filename
    
    target_name = os.path.basename(filename)
    for root, _, files in os.walk(current_extract_folder):
        for file in files:
            if file.lower() == target_name.lower():
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, current_extract_folder)
                return rel_path
    
    return None

def classify_intent(question, history=None):
    q_lower = question.lower().strip()
    filepath = extract_file_path(question)
    
    context_references = [
        r'\b(this|that|the above|the previous)\s+(code|function|file|snippet)\b',
        r'\bexplain\s+(this|that|it)\b',
        r'\bhow\s+does\s+(this|that|it)\s+work\b',
        r'\bwhat\s+does\s+(this|that|it)\s+do\b'
    ]
    
    if history and any(re.search(p, q_lower) for p in context_references):
        return 'explain_previous', None
    
    logic_patterns = [
        r'\bimportant\s+(logic|code)\b',
        r'\bmain\s+(logic|code|function)\b',
        r'\bkey\s+(logic|code|function)\b',
        r'\bcore\s+(logic|functionality)\b',
        r'\bmajor\s+(logic|code)\b'
    ]
    if any(re.search(p, q_lower) for p in logic_patterns):
        return 'show_logic', None
    
    greeting_patterns = [
        r'^(hi|hello|hey)$',
        r'^good\s+(morning|afternoon|evening)$',
        r'^how\s+are\s+you',
        r"^what'?s\s+up"
    ]
    if any(re.search(p, q_lower) for p in greeting_patterns):
        return 'greeting', None
    
    tree_patterns = [
        r'\bfile\s+tree\b',
        r'\bproject\s+structure\b',
        r'\bshow\s+(me\s+)?(the\s+)?tree\b',
        r'\blist\s+(all\s+)?files?\b',
        r'\bshow\s+(all\s+)?files?\b',
        r'\bwhat\s+files?\b',
        r'\bfile\s+(names?|structure|list)\b',
        r'\bdisplay\s+files?\b',
        r'\brepository\s+structure\b',
        r'\blist\s+file\b',
        r'\blit\s+files?\b',
        r'\bmain\s+files?\b',
        r'\bimportant\s+files?\b',
        r'\bkey\s+files?\b'
    ]
    if any(re.search(p, q_lower) for p in tree_patterns):
        return 'file_tree', None
    
    if filepath:
        show_code_patterns = [
            r'\bshow\s+(me\s+)?(the\s+)?code\b',
            r'\bdisplay\s+(the\s+)?code\b',
            r'\bprint\s+(the\s+)?file\b',
            r'\bopen\b',
            r'\bgive\s+me\s+(the\s+)?file\b',
            r'\blet\s+me\s+see\s+(the\s+)?file\b',
            r'\bview\s+(the\s+)?file\s+contents?\b',
            r'\bshow\s+(the\s+)?content\b',
            r'\bdisplay\s+(the\s+)?content\b'
        ]
        if any(re.search(p, q_lower) for p in show_code_patterns):
            return 'show_code', filepath
        
        explain_patterns = [
            r'\bhow\s+(does\s+)?.*\bworks?\b',
            r'\bow\s+.*\bworks?\b',
            r'\bexplain\b',
            r'\bwhat\s+does\b.*\bdo\b',
            r'\bdescribe\b',
            r'\bsummarize\b',
            r'\bsummary\b',
            r'\bhow\s+.*\bworks?\b'
        ]
        if any(re.search(p, q_lower) for p in explain_patterns):
            return 'explain_code', filepath
        
        modify_patterns = [
            r'\bfix\b',
            r'\bimprove\b',
            r'\brefactor\b',
            r'\boptimize\b',
            r'\bcorrect\s+error\b',
            r'\bhow to improve\b',
            r'\bsuggestions\b',
            r'\bbest practices\b'
        ]
        if any(re.search(p, q_lower) for p in modify_patterns):
            return 'modify_code', filepath
    
    return 'general_question', None

def get_file_extension_language(filepath):
    ext_map = {
        '.py': 'python', '.js': 'javascript', '.jsx': 'jsx', '.ts': 'typescript',
        '.tsx': 'tsx', '.html': 'html', '.css': 'css', '.json': 'json',
        '.md': 'markdown', '.java': 'java', '.cpp': 'cpp', '.c': 'c',
        '.go': 'go', '.rs': 'rust', '.php': 'php', '.rb': 'ruby',
        '.sh': 'bash', '.sql': 'sql', '.xml': 'xml', '.yaml': 'yaml', '.yml': 'yaml'
    }
    ext = os.path.splitext(filepath)[1].lower()
    return ext_map.get(ext, '')

def read_file_content(filepath):
    if not current_extract_folder:
        return None, "No files uploaded yet"
    
    filepath = filepath.replace('\\', '/').strip('/')
    full_path = os.path.normpath(os.path.join(current_extract_folder, filepath))
    
    if not full_path.startswith(os.path.normpath(current_extract_folder)):
        return None, "Invalid file path"
    
    if not os.path.exists(full_path):
        return None, f"File not found: {filepath}"
    
    if not os.path.isfile(full_path):
        return None, f"Not a file: {filepath}"
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, None
    except UnicodeDecodeError:
        return None, "Cannot read binary file"
    except Exception as e:
        return None, f"Error reading file: {str(e)}"

@app.route('/')
def home():
    return jsonify({"message": "RAG System Running"})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if username == 'demo' and password == 'demo':
        return jsonify({"token": "demo-token", "username": "demo"}), 200
    
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part in request"}), 400
        
        file = request.files['file']
        filename, error = save_uploaded_file(file)
        
        if error:
            return jsonify({"error": error}), 400
        
        logging.info(f"File uploaded: {filename}")
        
        file_path = os.path.join('uploads', filename)
        extract_folder = os.path.join('extracted', os.path.splitext(filename)[0])
        
        if filename.endswith('.zip'):
            logging.info("Extracting ZIP...")
            extract_zip(file_path, extract_folder)
            valid_files = get_code_files(extract_folder)
        else:
            valid_files = [file_path]
        
        if not valid_files:
            return jsonify({"error": "No valid files found"}), 400
        
        logging.info(f"Processing {len(valid_files)} files...")
        documents = chunk_files(valid_files)
        
        logging.info(f"Creating vector store with {len(documents)} chunks...")
        create_vector_store(documents)
        
        global uploaded_files, current_extract_folder
        uploaded_files = valid_files
        current_extract_folder = extract_folder if filename.endswith('.zip') else None
        
        return jsonify({
            "message": "File uploaded successfully",
            "filename": filename,
            "files_processed": len(valid_files),
            "chunks_created": len(documents)
        }), 200
    
    except Exception as e:
        logging.error(f"Upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/ask', methods=['POST'])
def ask_question():
    try:
        data = request.get_json()
        logging.info(f"Request data: {data}")
        
        if not data or 'question' not in data:
            return jsonify({"error": "Question is required"}), 400
        
        question = data['question']
        history = data.get('history', [])
        logging.info(f"Question received: {question}")
        logging.info(f"History length: {len(history)}")
        
        # Handle greetings and thanks first (before vector store check)
        greetings = ['hi', 'hello', 'hey']
        thanks = ['thank you', 'thanks', 'thankyou', 'thank u', 'thx']
        
        if question.lower().strip() in greetings:
            return jsonify({
                "question": question,
                "analysis": "Hi 👋 How can I help you with your code today?",
                "sources": []
            }), 200
        
        if any(thank in question.lower() for thank in thanks):
            return jsonify({
                "question": question,
                "analysis": "You're welcome! 😊 Feel free to ask if you need anything else.",
                "sources": []
            }), 200
        
        vector_store = load_vector_store()
        logging.info(f"Vector store loaded: {vector_store is not None}")
        
        if not vector_store:
            return jsonify({
                "question": question,
                "analysis": "Please upload your code ZIP file first, then I can answer questions about it!",
                "sources": []
            }), 200
        
        # Block unrelated questions - require at least 1 coding keyword or specific patterns
        coding_keywords = ['code', 'function', 'file', 'class', 'method', 'variable', 'component', 'module', 'import', 'export', 'css', 'html', 'javascript', 'python', 'java', 'react', 'api', 'database', 'server', 'frontend', 'backend', 'style', 'layout', 'button', 'form', 'input', 'output', 'error', 'bug', 'debug', 'test', 'build', 'deploy', 'package', 'dependency', 'library', 'framework', 'algorithm', 'data', 'array', 'object', 'string', 'number', 'boolean', 'loop', 'condition', 'syntax', 'logic', 'app', 'application', 'program', 'script', 'project', 'repository', 'git', 'npm', 'node', 'webpack', 'vite', 'work', 'works', 'does', 'explain', 'show', 'display', 'list', 'what', 'how', 'why', 'where']
        coding_question_patterns = [
            r'\b(explain|show|how|what|why|where)\s+',
            r'\b(improve|optimize|refactor|debug|fix)\s+',
            r'\.(js|py|css|html|jsx|tsx|java|cpp)\b',
            r'\bsummary\s+of\s+\w+\.(js|py|css|html)',
            r'\bproject\s+about\b',
            r'\bmain\s+files\b',
            r'\buser\s+function\b',
            r'\badd\s+user\b',
            r'\btech\s+stack\b',
            r'\btechnolog(y|ies)\s+(used|involved|stack)\b',
            r'\bsummarize\s+(the\s+)?project\b',
            r'\bproject\s+(summary|work|overview)\b',
            r'\bhow\s+does\s+(the\s+)?project\b',
            r'\bgive\s+summary\b',
            r'\bsummary\s+of\s+(my|the)\s+project\b',
        ]
        
        keyword_count = sum(1 for keyword in coding_keywords if keyword in question.lower())
        has_coding_pattern = any(re.search(pattern, question.lower()) for pattern in coding_question_patterns)
        
        if keyword_count < 1 and not has_coding_pattern:
            return jsonify({
                "question": question,
                "analysis": "I'm a code assistant. I can only help with questions about your uploaded code, programming concepts, or software development. Please ask about your project files or coding topics.",
                "sources": []
            }), 200
        
        intent, filepath = classify_intent(question, history)
        logging.info(f"Classified intent: {intent}, filepath: {filepath}")
        
        if filepath:
            logging.info(f"Attempting to find file: {filepath}")
        
        # Check if user is asking to explain a specific file (before vector search)
        filepath_in_question = extract_file_path(question)
        if filepath_in_question and any(keyword in question.lower() for keyword in ['explain', 'how does', 'what does', 'describe', 'purpose of', 'what is', 'explain the code']) and 'show' not in question.lower():
            found_path = find_file_in_repository(filepath_in_question)
            if found_path:
                try:
                    content, error = read_file_content(found_path)
                    if not error:
                        clean_path = clean_file_path(found_path)
                        context = f"File: {clean_path}\n\n{content[:1500]}"
                        analysis = generate_architecture_analysis(question, context)
                        return jsonify({
                            "question": question,
                            "analysis": analysis,
                            "sources": [clean_path]
                        }), 200
                except Exception as e:
                    logging.error(f"Error explaining file: {str(e)}")
        
        # Check if user provided code directly in their question
        code_in_question = None
        if any(keyword in question.lower() for keyword in ['explain this', 'what does this', 'how does this', 'explain the code', 'what is this']):
            # Check if question contains code patterns
            code_patterns = [
                r'\{[^}]+\}',  # CSS/JS blocks
                r'function\s+\w+',  # JS function
                r'const\s+\w+\s*=',  # JS const
                r'let\s+\w+\s*=',  # JS let
                r'var\s+\w+\s*=',  # JS var
                r'<\w+[^>]*>',  # HTML tags
                r'def\s+\w+',  # Python function
                r'class\s+\w+',  # Class definition
                r'import\s+',  # Import statement
                r'#\w+\s*\{',  # CSS ID selector
                r'\.\w+\s*\{',  # CSS class selector
            ]
            for pattern in code_patterns:
                if re.search(pattern, question):
                    code_in_question = question
                    break
        
        if code_in_question:
            try:
                analysis = generate_architecture_analysis("Explain this code", code_in_question)
                return jsonify({
                    "question": question,
                    "analysis": analysis,
                    "sources": []
                }), 200
            except Exception as e:
                logging.error(f"Error explaining provided code: {str(e)}")
                return jsonify({
                    "question": question,
                    "analysis": "I encountered an error analyzing the code. Please ensure Ollama is running.",
                    "sources": []
                }), 200
        
        if intent == 'explain_previous':
            if not history or len(history) < 2:
                return jsonify({
                    "question": question,
                    "analysis": "I don't see any previous code in our conversation. Please ask about a specific file or search for code first.",
                    "sources": []
                }), 200
            
            last_code_context = None
            for msg in reversed(history):
                if msg.get('role') == 'assistant' and '```' in msg.get('content', ''):
                    last_code_context = msg.get('content')
                    break
            
            if not last_code_context:
                return jsonify({
                    "question": question,
                    "analysis": "I don't see any code in our recent conversation. Please specify which file you'd like me to explain.",
                    "sources": []
                }), 200
            
            workflow_keywords = ['how does this work', 'how this works', 'workflow', 'flow', 'process']
            wants_workflow = any(keyword in question.lower() for keyword in workflow_keywords)
            
            if wants_workflow:
                prompt = f"""The user is asking about the workflow of this code:

{last_code_context}

Question: {question}

Provide a brief workflow explanation:
1. Start with what the code does (1 sentence)
2. List the main steps in order (3-5 bullet points)
3. End with the final outcome (1 sentence)

Keep it concise and focus on the flow, not implementation details."""
            else:
                prompt = f"""The user previously saw this code:

{last_code_context}

Now they're asking: {question}

Provide a clear explanation of how the code works, what it does, and answer their specific question."""
            
            analysis = generate_architecture_analysis(question, last_code_context)
            return jsonify({
                "question": question,
                "analysis": analysis,
                "sources": []
            }), 200
        
        if intent == 'show_logic':
            if not history or len(history) < 2:
                return jsonify({
                    "question": question,
                    "analysis": "Please specify which file you'd like to see the important logic from, or ask about a specific file first.",
                    "sources": []
                }), 200
            
            last_code_context = None
            last_file = None
            for msg in reversed(history):
                if msg.get('role') == 'assistant':
                    content = msg.get('content', '')
                    if '```' in content:
                        last_code_context = content
                        file_match = re.search(r'File:\s*\*\*(.+?)\*\*', content)
                        if file_match:
                            last_file = file_match.group(1)
                        break
            
            if not last_code_context:
                return jsonify({
                    "question": question,
                    "analysis": "I don't see any code in our recent conversation. Please ask about a specific file first.",
                    "sources": []
                }), 200
            
            code_blocks = re.findall(r'```[\w]*\n(.+?)\n```', last_code_context, re.DOTALL)
            
            if code_blocks:
                response = f"**Important logic from {last_file or 'the file'}:**\n\n"
                for i, code in enumerate(code_blocks, 1):
                    lang = get_file_extension_language(last_file) if last_file else ''
                    response += f"```{lang}\n{code.strip()}\n```\n\n"
                
                return jsonify({
                    "question": question,
                    "analysis": response,
                    "sources": [last_file] if last_file else []
                }), 200
            
            return jsonify({
                "question": question,
                "analysis": "I couldn't extract the important logic. Please try asking about a specific file.",
                "sources": []
            }), 200
        
        if intent == 'greeting':
            return jsonify({
                "question": question,
                "analysis": "Hi 👋 How can I help you with your code today?",
                "sources": []
            }), 200
        
        if intent == 'file_tree':
            if not current_extract_folder or not os.path.exists(current_extract_folder):
                return jsonify({
                    "question": question,
                    "analysis": "No files uploaded yet. Please upload a ZIP file first.",
                    "sources": []
                }), 200
            
            tree = generate_file_tree()
            return jsonify({
                "question": question,
                "analysis": f"```\n{tree}\n```",
                "sources": []
            }), 200
        
        # Handle "what is my project about" questions
        if any(pattern in question.lower() for pattern in ['project about', 'about this project', 'project work', 'does my project', 'summarize the project', 'summarize project', 'project summary', 'overview of project', 'what does this project', 'summary of my project', 'summary of the project', 'give summary']):
            # Look for README.md in the uploaded project
            readme_path = find_file_in_repository('README.md')
            if readme_path:
                content, error = read_file_content(readme_path)
                if not error and content:
                    # Extract first few paragraphs, remove markdown formatting
                    # Remove markdown headers, code blocks, and links
                    clean_content = re.sub(r'```[\s\S]*?```', '', content)
                    clean_content = re.sub(r'#+\s+', '', clean_content)
                    clean_content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean_content)
                    summary = '\n'.join(clean_content.split('\n')[:15])[:600]
                    
                    try:
                        if 'how does' in question.lower() or 'work' in question.lower():
                            prompt = f"""Explain how this project works in 4-5 simple sentences. Focus on the workflow and main features.

README content:
{summary}

Provide ONLY the explanation, nothing else."""
                        else:
                            prompt = f"""Summarize this project README in exactly 3-4 simple sentences. Focus on what the project does and its main purpose.

README content:
{summary}

Provide ONLY the summary, nothing else."""
                        analysis = generate_architecture_analysis(prompt, summary)
                        return jsonify({
                            "question": question,
                            "analysis": analysis,
                            "sources": [clean_file_path(readme_path)]
                        }), 200
                    except:
                        pass
            
            # If no README, analyze project structure from code files
            return jsonify({
                "question": question,
                "analysis": "I don't have a README file, but I can help you understand your project. Try asking:\n\n• 'list files' - See all files in your project\n• 'show code of [filename]' - View a specific file\n• 'explain [filename]' - Get explanation of a file\n• 'what is the main logic' - See important code sections",
                "sources": []
            }), 200
        
        if intent == 'show_code':
            found_path = find_file_in_repository(filepath)
            if not found_path:
                return jsonify({
                    "question": question,
                    "analysis": f"File not found: {filepath}",
                    "sources": []
                }), 200
            
            content, error = read_file_content(found_path)
            if error:
                return jsonify({"question": question, "analysis": error, "sources": []}), 200
            
            clean_path = clean_file_path(found_path)
            lang = get_file_extension_language(found_path)
            formatted_content = f"```{lang} id=\"codeblock\"\n{content}\n```"
            return jsonify({
                "question": question,
                "analysis": f"File: **{clean_path}**\n\n{formatted_content}",
                "sources": [clean_path]
            }), 200
        
        if intent == 'explain_code':
            found_path = find_file_in_repository(filepath)
            if not found_path:
                return jsonify({
                    "question": question,
                    "analysis": f"File not found: {filepath}",
                    "sources": []
                }), 200
            
            try:
                content, error = read_file_content(found_path)
                if error:
                    return jsonify({"question": question, "analysis": error, "sources": []}), 200
                
                clean_path = clean_file_path(found_path)
                context = f"File: {clean_path}\n\n{content[:2000]}"
                analysis = generate_architecture_analysis(question, context)
                return jsonify({
                    "question": question,
                    "analysis": analysis,
                    "sources": [clean_path]
                }), 200
            except Exception as e:
                logging.error(f"Error explaining code: {str(e)}")
                return jsonify({
                    "question": question,
                    "analysis": f"I found the file but encountered an error. Try asking: 'how does {filepath} work'",
                    "sources": []
                }), 200
        
        if intent == 'modify_code':
            found_path = find_file_in_repository(filepath)
            if not found_path:
                return jsonify({
                    "question": question,
                    "analysis": f"File not found: {filepath}",
                    "sources": []
                }), 200
            
            content, error = read_file_content(found_path)
            if error:
                return jsonify({"question": question, "analysis": error, "sources": []}), 200
            
            clean_path = clean_file_path(found_path)
            context = f"File: {clean_path}\n\n{content[:2000]}"
            analysis = generate_architecture_analysis(question, context)
            return jsonify({
                "question": question,
                "analysis": analysis,
                "sources": [clean_path]
            }), 200
        
        logging.info("Using vector search for semantic query...")
        results = vector_store.similarity_search(question, k=3)
        
        logging.info(f"Vector search returned {len(results) if results else 0} results")
        
        has_relevant_context = results and len(results) > 0
        
        if not has_relevant_context:
            logging.warning(f"No context found for question: {question}")
            return jsonify({
                "question": question,
                "analysis": "I couldn't find any information related to your question in the uploaded project. Please ask questions about the code in your repository.",
                "sources": []
            }), 200
        
        explanation_keywords = ['how does', 'how do', 'explain', 'what does', 'what is', 'describe', 'why does', 'about', 'summary', 'summarize', 'give summary', 'tech stack', 'technologies', 'what technologies']
        show_code_keywords = ['show', 'display', 'give me', 'show me', 'print']
        improve_keywords = ['improve', 'suggestions', 'best practices', 'how to improve', 'optimize', 'refactor', 'better']
        
        wants_explanation = any(keyword in question.lower() for keyword in explanation_keywords)
        wants_code_display = any(keyword in question.lower() for keyword in show_code_keywords) and 'code' in question.lower()
        wants_improvement = any(keyword in question.lower() for keyword in improve_keywords)
        
        # Check if user is asking about a specific file
        filepath_in_question = extract_file_path(question)
        if filepath_in_question and wants_explanation:
            # Redirect to explain_code intent for full file explanation
            intent = 'explain_code'
            filepath = filepath_in_question
            
            found_path = find_file_in_repository(filepath)
            if found_path:
                try:
                    content, error = read_file_content(found_path)
                    if not error:
                        clean_path = clean_file_path(found_path)
                        context = f"File: {clean_path}\n\n{content[:5000]}"
                        analysis = generate_architecture_analysis(question, context)
                        return jsonify({
                            "question": question,
                            "analysis": analysis,
                            "sources": [clean_path]
                        }), 200
                except Exception as e:
                    logging.error(f"Error explaining file: {str(e)}")
        
        binary_extensions = {'.db', '.sqlite', '.png', '.jpg', '.jpeg', '.gif', '.zip', '.exe', '.dll', '.bin', '.pdf'}
        
        if wants_code_display:
            # Check if a specific file was mentioned
            filepath_in_question = extract_file_path(question)
            
            if filepath_in_question:
                # User asked to show a specific file
                found_path = find_file_in_repository(filepath_in_question)
                if found_path:
                    content, error = read_file_content(found_path)
                    if not error:
                        clean_path = clean_file_path(found_path)
                        lang = get_file_extension_language(found_path)
                        formatted_content = f"```{lang} id=\"codeblock\"\n{content}\n```"
                        return jsonify({
                            "question": question,
                            "analysis": f"File: **{clean_path}**\n\n{formatted_content}",
                            "sources": [clean_path]
                        }), 200
            
            # Check for function/section name
            function_name = extract_function_or_section(question)
            
            if function_name:
                response_parts = []
                sources = []
                
                for result in results:
                    source = result.metadata.get('source', 'unknown')
                    ext = os.path.splitext(source)[1].lower()
                    
                    if ext in binary_extensions:
                        continue
                    
                    code = result.page_content.strip()
                    if not code or function_name.lower() not in code.lower():
                        continue
                    
                    clean_source = clean_file_path(source)
                    lang = get_file_extension_language(source)
                    
                    response_parts.append(f"**File: {clean_source}**\n\n```{lang}\n{code}\n```")
                    sources.append(clean_source)
                
                if response_parts:
                    analysis = "\n\n---\n\n".join(response_parts)
                    return jsonify({
                        "question": question,
                        "analysis": analysis,
                        "sources": sources
                    }), 200
        
        if wants_explanation:
            code_snippets = []
            sources = []
            for result in results:
                source = result.metadata.get('source', 'unknown')
                ext = os.path.splitext(source)[1].lower()
                if ext not in binary_extensions:
                    clean_source = clean_file_path(source)
                    code_snippets.append(f"File: {clean_source}\n{result.page_content}")
                    sources.append(clean_source)
            
            if not code_snippets:
                return jsonify({
                    "question": question,
                    "analysis": "I couldn't find any information related to your question in the uploaded project. Please ask questions about the code in your repository.",
                    "sources": []
                }), 200
            
            function_name = extract_function_or_section(question)
            
            if function_name:
                filtered_snippets = []
                for snippet in code_snippets:
                    if function_name.lower() in snippet.lower():
                        filtered_snippets.append(snippet)
                
                if filtered_snippets:
                    # Filter out non-code files like .md
                    code_only_snippets = [s for s in filtered_snippets if not any(ext in s.lower() for ext in ['.md', 'readme', 'documentation'])]
                    if code_only_snippets:
                        filtered_snippets = code_only_snippets
                    
                    context = '\n\n'.join(filtered_snippets[:1])[:800]
                    
                    try:
                        analysis = generate_architecture_analysis(f"Explain the {function_name} function", context)
                    except Exception as e:
                        logging.error(f"Ollama error for function {function_name}: {str(e)}")
                        analysis = f"**{function_name} Function:**\n\nI found the {function_name} code but Ollama is not responding. Please ensure Ollama is running with `ollama serve` and try again.\n\nRelevant files: {', '.join(sources[:2])}"
                    
                    return jsonify({
                        "question": question,
                        "analysis": analysis,
                        "sources": sources
                    }), 200
            
            context = '\n\n'.join(code_snippets[:1])[:800]
            
            try:
                analysis = generate_architecture_analysis(question, context)
            except Exception as e:
                logging.error(f"Ollama error: {str(e)}")
                analysis = f"**Brief Summary:**\n\nThe code snippets found relate to your question about the project. The relevant files are: {', '.join(sources[:3])}. For a detailed explanation, please ensure Ollama is running (`ollama serve`) and try again."
            
            return jsonify({
                "question": question,
                "analysis": analysis,
                "sources": sources
            }), 200
        
        if wants_improvement:
            code_snippets = []
            sources = []
            for result in results:
                source = result.metadata.get('source', 'unknown')
                ext = os.path.splitext(source)[1].lower()
                if ext not in binary_extensions:
                    clean_source = clean_file_path(source)
                    code_snippets.append(f"File: {clean_source}\n{result.page_content}")
                    sources.append(clean_source)
            
            if code_snippets:
                context = '\n\n'.join(code_snippets[:1])[:800]
                
                try:
                    improvement_prompt = f"Provide code improvement suggestions for this code. List 3-5 specific improvements with explanations.\n\nCode:\n{context}"
                    analysis = generate_architecture_analysis(improvement_prompt, context)
                except Exception as e:
                    logging.error(f"Ollama error: {str(e)}")
                    analysis = "I found relevant code but encountered an error. Please ensure Ollama is running and try again."
                
                return jsonify({
                    "question": question,
                    "analysis": analysis,
                    "sources": sources
                }), 200
        
        response_parts = []
        sources = []
        
        for result in results:
            source = result.metadata.get('source', 'unknown')
            
            ext = os.path.splitext(source)[1].lower()
            if ext in binary_extensions:
                continue
            
            code = result.page_content.strip()
            if not code:
                continue
            
            clean_source = clean_file_path(source)
            lang = get_file_extension_language(source)
            
            response_parts.append(f"**File: {clean_source}**\n\n```{lang}\n{code}\n```")
            sources.append(clean_source)
        
        if not response_parts:
            return jsonify({
                "question": question,
                "analysis": "I couldn't find any information related to your question in the uploaded project. Please ask questions about the code in your repository.",
                "sources": []
            }), 200
        
        analysis = "\n\n---\n\n".join(response_parts)
        
        return jsonify({
            "question": question,
            "analysis": analysis,
            "sources": sources
        }), 200
    
    except Exception as e:
        logging.error(f"Error in ask_question: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "question": question,
            "analysis": f"Error: {str(e)}. Please check backend logs for details.",
            "sources": []
        }), 200

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
