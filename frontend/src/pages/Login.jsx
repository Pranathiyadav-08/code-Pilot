import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../api';
import './Login.css';

function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await login(username, password);
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('currentUser', response.data.username);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setUsername('demo');
    setPassword('demo');
    setError('');
    setLoading(true);

    try {
      const response = await login('demo', 'demo');
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('currentUser', response.data.username);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-left">
        <div className="glow-orb"></div>
        <div className="brand">
          <div className="brand-icon"></div>
          <h1>CodePilot</h1>
          <p>AI-Powered Code Intelligence Platform</p>
        </div>
      </div>
      
      <div className="login-right">
        <div className="login-card">
          <h2>Welcome Back</h2>
          <p className="subtitle">Sign in to continue your journey</p>
          
          <form onSubmit={handleSubmit}>
            <div className="input-group">
              <label>Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                required
              />
            </div>
            
            <div className="input-group">
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
              />
            </div>
            
            {error && <div className="error-box">{error}</div>}
            
            <button type="submit" className="btn-login" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
            
            <button type="button" onClick={handleDemoLogin} className="btn-demo" disabled={loading}>
              Demo Login
            </button>
          </form>
          
          <div className="footer">
            <p>Don't have an account?</p>
            <button onClick={() => navigate('/signup')} className="btn-link">
              Create Account
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;
