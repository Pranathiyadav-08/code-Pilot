from flask import Blueprint, request, jsonify
import os
import re
from services.vector_store import load_vector_store
from services.llm_service import generate_architecture_analysis
from utils.helpers import (
    clean_file_path, get_file_extension_language, extract_file_path,
    extract_function_or_section, classify_intent
)
from utils.logger import logger

chat_bp = Blueprint('chat', __name__, url_prefix='/api')

def get_current_extract_folder():
    from routes.upload_routes import get_state
    _, folder = get_state()
    return folder

def get_file_list():
    current_extract_folder = get_current_extract_folder()
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
    current_extract_folder = get_current_extract_folder()
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

def find_file_in_repository(filename):
    current_extract_folder = get_current_extract_folder()
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

def read_file_content(filepath):
    current_extract_folder = get_current_extract_folder()
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

@chat_bp.route('/ask', methods=['POST'])
def ask_question():
    try:
        data = request.get_json()
        logger.info(f"Request data: {data}")
        
        if not data or 'question' not in data:
            return jsonify({"error": "Question is required"}), 400
        
        question = data['question']
        history = data.get('history', [])
        logger.info(f"Question received: {question}")
        
        # Handle greetings and thanks
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
        logger.info(f"Vector store loaded: {vector_store is not None}")
        
        if not vector_store:
            return jsonify({
                "question": question,
                "analysis": "Please upload your code ZIP file first, then I can answer questions about it!",
                "sources": []
            }), 200
        
        # Validate coding-related questions
        coding_keywords = ['code', 'function', 'file', 'class', 'method', 'variable', 'component', 'module', 'import', 'export', 'css', 'html', 'javascript', 'python', 'java', 'react', 'api', 'database', 'server', 'frontend', 'backend', 'style', 'layout', 'button', 'form', 'input', 'output', 'error', 'bug', 'debug', 'test', 'build', 'deploy', 'package', 'dependency', 'library', 'framework', 'algorithm', 'data', 'array', 'object', 'string', 'number', 'boolean', 'loop', 'condition', 'syntax', 'logic', 'app', 'application', 'program', 'script', 'project', 'repository', 'git', 'npm', 'node', 'webpack', 'vite', 'work', 'works', 'does', 'explain', 'show', 'display', 'list', 'what', 'how', 'why', 'where']
        coding_question_patterns = [
            r'\b(explain|show|how|what|why|where)\s+',
            r'\b(improve|optimize|refactor|debug|fix)\s+',
            r'\.(js|py|css|html|jsx|tsx|java|cpp)\b',
            r'\bproject\s+about\b',
            r'\bmain\s+files\b',
            r'\btech\s+stack\b',
            r'\btechnolog(y|ies)\s+(used|involved|stack)\b',
            r'\bsummarize\s+(the\s+)?project\b',
            r'\bproject\s+(summary|work|overview)\b',
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
        logger.info(f"Classified intent: {intent}, filepath: {filepath}")
        
        # Handle different intents
        if intent == 'greeting':
            return jsonify({
                "question": question,
                "analysis": "Hi 👋 How can I help you with your code today?",
                "sources": []
            }), 200
        
        if intent == 'file_tree':
            current_extract_folder = get_current_extract_folder()
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
        
        if intent == 'show_code' and filepath:
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
        
        if intent == 'explain_code' and filepath:
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
                logger.error(f"Error explaining code: {str(e)}")
                return jsonify({
                    "question": question,
                    "analysis": f"I found the file but encountered an error. Try asking: 'how does {filepath} work'",
                    "sources": []
                }), 200
        
        # Vector search for general questions
        logger.info("Using vector search for semantic query...")
        results = vector_store.similarity_search(question, k=3)
        logger.info(f"Vector search returned {len(results) if results else 0} results")
        
        if not results or len(results) == 0:
            return jsonify({
                "question": question,
                "analysis": "I couldn't find any information related to your question in the uploaded project. Please ask questions about the code in your repository.",
                "sources": []
            }), 200
        
        # Process results
        explanation_keywords = ['how does', 'how do', 'explain', 'what does', 'what is', 'describe', 'why does', 'about', 'summary', 'summarize']
        wants_explanation = any(keyword in question.lower() for keyword in explanation_keywords)
        
        binary_extensions = {'.db', '.sqlite', '.png', '.jpg', '.jpeg', '.gif', '.zip', '.exe', '.dll', '.bin', '.pdf'}
        
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
                    "analysis": "I couldn't find any information related to your question in the uploaded project.",
                    "sources": []
                }), 200
            
            context = '\n\n'.join(code_snippets[:1])[:800]
            
            try:
                analysis = generate_architecture_analysis(question, context)
            except Exception as e:
                logger.error(f"Ollama error: {str(e)}")
                analysis = f"**Brief Summary:**\n\nThe code snippets found relate to your question. The relevant files are: {', '.join(sources[:3])}. For a detailed explanation, please ensure Ollama is running (`ollama serve`) and try again."
            
            return jsonify({
                "question": question,
                "analysis": analysis,
                "sources": sources
            }), 200
        
        # Default: return code snippets
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
                "analysis": "I couldn't find any information related to your question in the uploaded project.",
                "sources": []
            }), 200
        
        analysis = "\n\n---\n\n".join(response_parts)
        
        return jsonify({
            "question": question,
            "analysis": analysis,
            "sources": sources
        }), 200
    
    except Exception as e:
        logger.error(f"Error in ask_question: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "question": question if 'question' in locals() else '',
            "analysis": f"Error: {str(e)}. Please check backend logs for details.",
            "sources": []
        }), 200
