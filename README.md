# RAG Document Query System

Upload any file (ZIP, DOCX, PDF, TXT, code files) and ask questions about it in natural language. Get simple, clear answers powered by AI.

## Features
- 📁 Upload ZIP files, documents, or code files
- 🤖 AI-powered answers using Ollama (runs locally)
- 💬 Ask questions in plain English
- 📄 Supports: .docx, .pdf, .txt, .py, .js, .md, .json, and more
- 🔒 All data stays on your computer

---

## Prerequisites

1. **Python 3.8+** - [Download](https://www.python.org/downloads/)
2. **Node.js 16+** - [Download](https://nodejs.org/)
3. **Ollama** - [Download](https://ollama.ai/)

---

## Setup Instructions

### Step 1: Install Ollama & Download Model

```bash
# Install Ollama from https://ollama.ai
# Then download the AI model:
ollama pull gemma:2b
```

### Step 2: Setup Backend

```bash
# Navigate to backend folder
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Start the backend server
python app.py
```

Backend will run on: `http://localhost:5000`

### Step 3: Setup Frontend

Open a **new terminal** window:

```bash
# Navigate to frontend folder
cd frontend

# Install dependencies
npm install

# Start the frontend
npm run dev
```

Frontend will run on: `http://localhost:5173`

### Step 4: Start Ollama (if not running)

Open a **third terminal** window:

```bash
ollama serve
```

---

## How to Use

1. **Login**: Click "Demo Login" button (auto-fills credentials)
2. **Upload**: Choose a ZIP file or document
3. **Ask**: Type questions like:
   - "What is this project about?"
   - "How many files are in the upload?"
   - "Explain the main features"
4. **Get Answers**: AI reads your files and explains in simple language

---

## Project Structure

```
cbn/
├── backend/
│   ├── services/          # Core logic
│   ├── uploads/           # Uploaded files
│   ├── extracted/         # Extracted ZIP contents
│   ├── vector_store/      # AI embeddings
│   ├── app.py            # Main server
│   └── requirements.txt   # Python packages
│
└── frontend/
    ├── src/
    │   ├── pages/        # Login & Dashboard
    │   ├── components/   # UI components
    │   └── api.js        # Backend API calls
    └── package.json      # Node packages
```

---

## Troubleshooting

### Backend won't start
```bash
# Make sure you're in backend folder
cd backend
pip install -r requirements.txt
python app.py
```

### Frontend won't start
```bash
# Make sure you're in frontend folder
cd frontend
npm install
npm run dev
```

### "Connection refused" error
- Make sure Ollama is running: `ollama serve`
- Check backend is running on port 5000
- Check frontend is running on port 5173

### Upload fails
- File must be under 50MB
- For ZIP files, ensure they contain text-based files
- Binary files like images are skipped

### Slow responses
- First upload downloads AI model (takes time)
- Gemma:2b is lightweight but may take 10-30 seconds per answer
- For faster responses, use a more powerful model: `ollama pull llama3`

---

## Tech Stack

**Backend:**
- Flask (Python web server)
- LangChain (Document processing)
- FAISS (Vector search)
- Sentence Transformers (Embeddings)
- python-docx & PyPDF2 (Document readers)

**Frontend:**
- React + Vite
- Axios (API calls)

**AI:**
- Ollama (Local LLM)
- Gemma 2B (Language model)

---

## Demo Credentials

- Username: `demo`
- Password: `demo`

---

## Notes

- All processing happens locally on your machine
- No data is sent to external servers
- First upload takes longer (downloads embedding model)
- Supports multiple file types in ZIP archives
- AI responses are generated based only on uploaded files

---

## Support

For issues or questions, check:
1. All three services are running (Backend, Frontend, Ollama)
2. Ports 5000, 5173, and 11434 are not blocked
3. Python and Node.js are properly installed
