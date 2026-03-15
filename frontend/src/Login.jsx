import { useState } from 'react';
import './Login.css';

function Login({ onLogin }) {
  const [isSignup, setIsSignup] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (isSignup) {
      // Signup logic
      if (password !== confirmPassword) {
        setError('Passwords do not match');
        return;
      }
      if (password.length < 6) {
        setError('Password must be at least 6 characters');
        return;
      }

      const users = JSON.parse(localStorage.getItem('users') || '{}');
      
      if (users[username]) {
        setError('Username already exists');
        return;
      }

      users[username] = password;
      localStorage.setItem('users', JSON.stringify(users));
      setError('');
      setIsSignup(false);
      alert('Account created! Please login.');
      setUsername('');
      setPassword('');
      setConfirmPassword('');
    } else {
      // Login logic
      const users = JSON.parse(localStorage.getItem('users') || '{}');
      
      if (users[username] && users[username] === password) {
        onLogin(username);
      } else {
        setError('Invalid username or password');
      }
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>RAG ZIP System</h1>
        <p className="subtitle">{isSignup ? 'Create Account' : 'Login to continue'}</p>
        
        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              required
            />
          </div>
          
          <div className="input-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
            />
          </div>
          
          {isSignup && (
            <div className="input-group">
              <label>Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter your password"
                required
              />
            </div>
          )}
          
          {error && <div className="error-msg">{error}</div>}
          
          <button type="submit" className="login-btn">
            {isSignup ? 'Sign Up' : 'Login'}
          </button>
        </form>
        
        <div className="toggle-auth">
          <p>{isSignup ? 'Already have an account?' : "Don't have an account?"}</p>
          <button 
            type="button" 
            onClick={() => {
              setIsSignup(!isSignup);
              setError('');
              setConfirmPassword('');
            }}
            className="toggle-btn"
          >
            {isSignup ? 'Login Here' : 'Sign Up Here'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default Login;
