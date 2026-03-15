# RAG File Query System - Setup Guide

## What This Does
Users can upload ZIP files, individual files, or folders and ask natural language questions. Get human-like responses with source file references.

## Quick Setup

### 1. Install Ollama & Pull Model
```bash
# Install Ollama from https://ollama.ai
# Then pull the model:
ollama pull gemma:2b
```

### 2. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3. Run Ollama (keep running)
```bash
ollama serve
```

### 4. Run Backend
```bash
cd backend
python app.py
```

### 5. Run Frontend
```bash
cd frontend
npm install
npm run dev
```

## Example Usage

**Upload**: `project.zip`

**Query**: "What does the authentication function do?"

**Response**: "The authentication system uses JWT tokens. In auth.py, the login function validates credentials and generates a token with 24-hour expiration."

✅ Supports zip/individual files
✅ Natural responses via Ollama gemma:2b
✅ Shows source files
