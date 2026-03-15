import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadZip, askQuestion } from '../api';
import ChatResponse from '../components/ChatResponse';
import '../App.css';

function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState('');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const currentUser = localStorage.getItem('currentUser');
    if (!currentUser) {
      navigate('/login');
    } else {
      setUser(currentUser);
    }
  }, [navigate]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleLogout = () => {
    localStorage.removeItem('currentUser');
    navigate('/login');
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.name.endsWith('.zip')) {
      setFile(selectedFile);
      setError('');
    } else {
      setError('Please select a .zip file');
      setFile(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setUploading(true);
    setError('');
    try {
      const response = await uploadZip(file);
      setUploadResult(response.data);
      setFile(null);
    } catch (err) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;
    
    const userQuestion = question;
    setMessages(prev => [...prev, { role: 'user', type: 'question', content: userQuestion }]);
    setQuestion('');
    setAsking(true);
    setError('');
    
    try {
      // Prepare conversation history for backend
      const history = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));
      
      const response = await askQuestion(userQuestion, history);
      setMessages(prev => [...prev, { role: 'assistant', type: 'answer', content: response.data.analysis }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', type: 'answer', content: 'Backend server is not running. Please start the backend server.' }]);
    } finally {
      setAsking(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <div className="logo-icon">🚀</div>
            <div className="logo-text">
              <h1>CodePilot</h1>
              <p>AI-Powered Code Intelligence</p>
            </div>
          </div>
          <div className="user-section">
            <span className="user-info">{user}</span>
            <button onClick={handleLogout} className="logout-btn">
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="main-layout">
        <aside className="sidebar">
          <div className="card">
            <div className="card-header">
              <span className="card-icon">📦</span>
              <h2 className="card-title">Upload</h2>
            </div>
            
            <input
              type="file"
              accept=".zip"
              onChange={handleFileChange}
              id="file-input"
            />
            <label htmlFor="file-input" className="upload-area">
              <div className="upload-icon">☁️</div>
              <div className="upload-text">
                {file ? file.name : 'Drop ZIP here'}
              </div>
              <div className="upload-hint">or click to browse</div>
            </label>
            
            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="btn-primary"
            >
              {uploading ? '⏳ Processing...' : '🚀 Upload'}
            </button>

            {uploadResult && (
              <div className="status-box success">
                <p>✅ {uploadResult.message}</p>
                <p>📄 {uploadResult.files_processed} files | {uploadResult.chunks_created} chunks</p>
              </div>
            )}

            {error && !uploadResult && (
              <div className="status-box error">
                ❌ {error}
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-icon">📊</span>
              <h2 className="card-title">Stats</h2>
            </div>
            <div className="stats-grid">
              <div className="stat-item">
                <span>💬</span>
                <span>Messages: {messages.length}</span>
              </div>
              <div className="stat-item">
                <span>📁</span>
                <span>File: {uploadResult?.filename || 'None'}</span>
              </div>
              <div className="stat-item">
                <span>🔍</span>
                <span>Status: {asking ? 'Analyzing...' : 'Ready'}</span>
              </div>
            </div>
          </div>
        </aside>

        <main className="chat-container">
          <div className="chat-header">
            <div className="card-header">
              <span className="card-icon">💬</span>
              <h2 className="card-title">Chat with Your Code</h2>
            </div>
          </div>

          <div className="chat-messages">
            {messages.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">💭</div>
                <h3>Start a conversation</h3>
                <p>Upload your code and ask questions about it</p>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.type}`}>
                  <div className="message-label">
                    {msg.type === 'question' ? '🤔 You' : '🤖 AI'}
                  </div>
                  <div className="message-content">
                    {msg.type === 'answer' ? <ChatResponse answer={msg.content} /> : msg.content}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input-area">
            <form onSubmit={handleAsk} className="chat-input-wrapper">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask anything about your code..."
                className="chat-input"
                disabled={asking}
              />
              <button
                type="submit"
                disabled={!question.trim() || asking}
                className="btn-send"
              >
                {asking ? '⏳' : '🚀'}
              </button>
            </form>
          </div>
        </main>
      </div>
    </div>
  );
}

export default Dashboard;
