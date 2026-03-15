import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads'
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'zip', 'txt', 'py', 'js', 'java', 'cpp', 'c', 'h', 'cs', 'rb', 'go', 'rs', 'php', 'html', 'css', 'json', 'xml', 'md', 'yaml', 'yml', 'ts', 'jsx', 'tsx', 'vue', 'swift', 'kt', 'scala', 'r', 'sql', 'sh'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    if not file:
        return None, "No file provided"
    
    if file.filename == '':
        return None, "No file selected"
    
    if not allowed_file(file.filename):
        return None, "Only .zip files are allowed"
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    file.save(filepath)
    return filename, None
