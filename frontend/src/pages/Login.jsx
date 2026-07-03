import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogIn, Shield, Mail, Lock, Loader2 } from 'lucide-react';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [isSSO, setIsSSO] = useState(false);
  const [isSubmitting, setIsSSubmitting] = useState(false);
  
  const { login, ssoLogin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/dashboard";

  const handleStandardLogin = async (e) => {
    e.preventDefault();
    setError('');
    setIsSSubmitting(true);
    try {
      const success = await login(username, password);
      if (success) {
        navigate(from, { replace: true });
      } else {
        setError('Invalid username or password');
      }
    } catch (err) {
      setError('An error occurred during login');
    } finally {
      setIsSSubmitting(false);
    }
  };

  const handleSSOLogin = async (e) => {
    e.preventDefault();
    setError('');
    setIsSSubmitting(true);
    try {
      const success = await ssoLogin(email, 'enterprise-sso');
      if (success) {
        navigate(from, { replace: true });
      } else {
        setError('SSO Login failed. Ensure the email is correct.');
      }
    } catch (err) {
      setError('An error occurred during SSO login');
    } finally {
      setIsSSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card card">
        <div className="login-header">
          <div className="logo-icon">P</div>
          <h1>PriorityFlow</h1>
          <p>Sign in to your account</p>
        </div>

        {error && <div className="login-error">{error}</div>}

        <div className="login-tabs">
          <button 
            className={`tab-btn ${!isSSO ? 'active' : ''}`} 
            onClick={() => setIsSSO(false)}
          >
            Standard
          </button>
          <button 
            className={`tab-btn ${isSSO ? 'active' : ''}`} 
            onClick={() => setIsSSO(true)}
          >
            Enterprise SSO
          </button>
        </div>

        {!isSSO ? (
          <form onSubmit={handleStandardLogin}>
            <div className="form-group">
              <label><Mail size={16} /> Username</label>
              <input 
                type="text" 
                value={username} 
                onChange={(e) => setUsername(e.target.value)} 
                required 
                placeholder="e.g. john"
              />
            </div>
            <div className="form-group">
              <label><Lock size={16} /> Password</label>
              <input 
                type="password" 
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                required 
                placeholder="••••••••"
              />
            </div>
            <button type="submit" className="login-btn" disabled={isSubmitting}>
              {isSubmitting ? <Loader2 className="spin" size={20} /> : <><LogIn size={18} /> Sign In</>}
            </button>
          </form>
        ) : (
          <form onSubmit={handleSSOLogin}>
            <div className="form-group">
              <label><Mail size={16} /> Enterprise Email</label>
              <input 
                type="email" 
                value={email} 
                onChange={(e) => setEmail(e.target.value)} 
                required 
                placeholder="name@company.com"
              />
            </div>
            <button type="submit" className="login-btn sso" disabled={isSubmitting}>
              {isSubmitting ? <Loader2 className="spin" size={20} /> : <><Shield size={18} /> Continue with SSO</>}
            </button>
          </form>
        )}

        <div className="login-footer">
          <p>Demo accounts: admin/admin123, john/password</p>
        </div>
      </div>
    </div>
  );
};

export default Login;
