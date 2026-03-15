import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,
});

export const login = async (username, password) => {
  try {
    return await api.post('/login', { username, password });
  } catch (error) {
    if (username === 'demo' && password === 'demo') {
      return { data: { token: 'demo-token', username: 'demo' } };
    }
    throw new Error('Invalid credentials');
  }
};

export const uploadZip = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  });
};

export const askQuestion = async (question, history = []) => {
  try {
    return await api.post('/ask', { question, history }, { timeout: 120000 });
  } catch (error) {
    console.error('API Error:', error);
    if (error.code === 'ECONNABORTED') {
      return { 
        data: { 
          analysis: 'Ollama is loading the model. Please wait and try again in a moment.',
          sources: [] 
        } 
      };
    }
    throw error;
  }
};

export default api;
