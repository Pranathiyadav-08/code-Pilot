from flask import Flask, jsonify
from flask_cors import CORS
import os
from config import Config
from utils.logger import setup_logger
from routes.auth_routes import auth_bp
from routes.upload_routes import upload_bp
from routes.chat_routes import chat_bp

# Setup logging
setup_logger()

# Initialize Flask app
app = Flask(__name__)

# Configure CORS
CORS(app, resources={
    r"/*": {
        "origins": Config.CORS_ORIGINS,
        "methods": Config.CORS_METHODS,
        "allow_headers": Config.CORS_HEADERS
    }
})

# Configure app
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_FILE_SIZE
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER

# Create necessary directories
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.EXTRACT_FOLDER, exist_ok=True)
os.makedirs(Config.VECTOR_STORE_FOLDER, exist_ok=True)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(chat_bp)

@app.route('/')
def home():
    return jsonify({"message": "RAG System Running"})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
