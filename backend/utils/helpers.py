import os
import re

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

def extract_file_path(question):
    patterns = [
        r'(?:code of|file|explain|show|summary of|summarize|content in|content of)\s+([\w\-]+\.[a-z]{1,5})\b',
        r'\b(readme\.md)\b',
        r'([\w\-]+/[\w\-/.]+\.[a-z]{1,5})',
        r'([\w\-]+\\[\w\-\\.]+\.[a-z]{1,5})',
        r'\b([A-Z][\w\-]*\.[a-z]{2,5})\b'
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            return match.group(1).replace('\\', '/')
    return None

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
