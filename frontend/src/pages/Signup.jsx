import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Login.css';

function Signup() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setLoading(true);
    setTimeout(() => {
      alert('Account created! Please login with demo/demo');
      navigate('/login');
      setLoading(false);
    }, 500);
  };

  return (
    <div className="login-container">
      <div className="login-left">
        <div className="glow-orb"></div>
        <div className="brand">
          <div className="brand-icon">🚀</div>
          <h1>CodePilot</h1>
          <p>AI-Powered Code Intelligence Platform</p>
        </div>
      </div>
      
      <div className="login-right">
        <div className="login-card">
          <h2>Create Account</h2>
          <p className="subtitle">Sign up to get started</p>
          
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
            
            <div className="input-group">
              <label>Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter password"
                required
              />
            </div>
            
            {error && <div className="error-box">{error}</div>}
            
            <button type="submit" className="btn-login" disabled={loading}>
              {loading ? '⏳ Creating...' : '🚀 Sign Up'}
            </button>
          </form>
          
          <div className="footer">
            <p>Already have an account?</p>
            <button onClick={() => navigate('/login')} className="btn-link">
              Login
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Signup;
