import os
import zipfile

IGNORED_DIRS = {'node_modules', '.git', 'dist', 'build', '__pycache__', 'venv', 'env'}
ALLOWED_EXTENSIONS = {'.py', '.js', '.ts', '.java', '.md', '.txt', '.json', '.html', '.css', '.jsx', '.tsx', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.sql', '.yaml', '.yml', '.xml', '.sh', '.bat', '.csv', '.ipynb'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

def extract_zip(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    return extract_to

def get_code_files(root_folder):
    valid_files = []
    
    for dirpath, dirnames, filenames in os.walk(root_folder):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            
            # Skip very large files
            try:
                if os.path.getsize(file_path) > MAX_FILE_SIZE:
                    continue
                valid_files.append(file_path)
            except:
                continue
    
    return valid_files
