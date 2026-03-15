from flask import Blueprint, request, jsonify

auth_bp = Blueprint('auth', __name__, url_prefix='/api')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if username == 'demo' and password == 'demo':
        return jsonify({"token": "demo-token", "username": "demo"}), 200
    
    return jsonify({"error": "Invalid credentials"}), 401
