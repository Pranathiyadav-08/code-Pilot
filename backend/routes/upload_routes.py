from flask import Blueprint, request, jsonify
import os
from services.file_handler import save_uploaded_file
from services.zip_processor import extract_zip, get_code_files
from services.chunker import chunk_files
from services.vector_store import create_vector_store
from utils.logger import logger
from config import Config

upload_bp = Blueprint('upload', __name__, url_prefix='/api')

uploaded_files = []
current_extract_folder = None

def get_state():
    return uploaded_files, current_extract_folder

def set_state(files, folder):
    global uploaded_files, current_extract_folder
    uploaded_files = files
    current_extract_folder = folder

@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part in request"}), 400
        
        file = request.files['file']
        filename, error = save_uploaded_file(file)
        
        if error:
            return jsonify({"error": error}), 400
        
        logger.info(f"File uploaded: {filename}")
        
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        extract_folder = os.path.join(Config.EXTRACT_FOLDER, os.path.splitext(filename)[0])
        
        if filename.endswith('.zip'):
            logger.info("Extracting ZIP...")
            extract_zip(file_path, extract_folder)
            valid_files = get_code_files(extract_folder)
        else:
            valid_files = [file_path]
        
        if not valid_files:
            return jsonify({"error": "No valid files found"}), 400
        
        logger.info(f"Processing {len(valid_files)} files...")
        documents = chunk_files(valid_files)
        
        logger.info(f"Creating vector store with {len(documents)} chunks...")
        create_vector_store(documents)
        
        set_state(valid_files, extract_folder if filename.endswith('.zip') else None)
        
        return jsonify({
            "message": "File uploaded successfully",
            "filename": filename,
            "files_processed": len(valid_files),
            "chunks_created": len(documents)
        }), 200
    
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
