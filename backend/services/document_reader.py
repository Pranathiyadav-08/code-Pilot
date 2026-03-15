import os

def read_file_content(file_path):
    """Read content from various file types"""
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == '.docx':
            from docx import Document
            doc = Document(file_path)
            return '\n'.join([para.text for para in doc.paragraphs])
        
        elif ext == '.pdf':
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            return '\n'.join([page.extract_text() for page in reader.pages])
        
        else:
            # Text files
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
    except:
        return ""
