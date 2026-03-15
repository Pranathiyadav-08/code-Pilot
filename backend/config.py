import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    UPLOAD_FOLDER = 'uploads'
    EXTRACT_FOLDER = 'extracted'
    VECTOR_STORE_FOLDER = 'vector_store'
    
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'gemma:2b')
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    
    CORS_ORIGINS = "*"
    CORS_METHODS = ["GET", "POST", "OPTIONS"]
    CORS_HEADERS = ["Content-Type"]
