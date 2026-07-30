import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ThemeToggle from '../components/ThemeToggle';
import { LogIn, Loader2, UserPlus, ArrowRight, Zap, CheckCircle2 } from 'lucide-react';

const Login = () => {
  const [mode, setMode] = useState('signin');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login, register, handleSSOCallback } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || '/dashboard';

  // If URL has ?mode=signup, start on sign-up form
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('mode') === 'signup') setMode('signup');
  }, [location.search]);

  // Listen for SSO popup messages
  useEffect(() => {
    const handler = (event) => {
      if (event.data?.type === 'sso-success' && event.data?.token) {
        handleSSOCallback(event.data.token, event.data.refresh_token);
        navigate(from, { replace: true });
      }
      if (event.data?.type === 'sso-error' && event.data?.message) {
        setError(event.data.message);
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [navigate, from, handleSSOCallback]);

  const openSSOPopup = useCallback((provider) => {
    setError('');
    const width = 500;
    const height = 600;
    const left = Math.max(0, (window.screen.width - width) / 2);
    const top = Math.max(0, (window.screen.height - height) / 2);
    const popup = window.open(
      `/#/sso-popup?provider=${provider}`,
      `sso_${provider}`,
      `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
    );
    if (!popup) {
      setError('Popup blocked. Please allow popups for this site.');
    }
  }, []);

  const handleSignIn = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      const success = await login(username, password);
      if (success) {
        navigate(from, { replace: true });
      } else {
        setError('Invalid username or password');
      }
    } catch {
      setError('An error occurred during login');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSignUp = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      const result = await register(username, email, password, name);
      if (result.success) {
        navigate('/onboarding', { replace: true });
      } else {
        setError(result.error || 'Registration failed. Try again.');
      }
    } catch {
      setError('An error occurred during registration');
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleMode = () => {
    setMode(mode === 'signin' ? 'signup' : 'signin');
    setError('');
  };

  return (
    <div className="auth-container">
      {/* Public route: no sidebar here, so the theme switch needs its own home. */}
      <ThemeToggle variant="pill" className="auth-theme-toggle" />
      <div className="auth-form-side">
        <div className="auth-form">
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: 'var(--radius-input)', background: 'var(--color-accent)', color: 'var(--color-accent-ink)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '18px' }}>C</div>
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: '20px', color: 'var(--color-ink)' }}>Clutsch</span>
          </div>

          {/* Heading */}
          <div>
            <h1 style={{ fontSize: '28px', marginBottom: '8px' }}>
              {mode === 'signin' ? 'Welcome back' : 'Create your account'}
            </h1>
            <p className="text-body" style={{ color: 'var(--color-ink-2)' }}>
              {mode === 'signin' ? 'Sign in to your Clutsch workspace.' : 'Start your 14-day free trial. No credit card needed.'}
            </p>
          </div>

          {error && (
            <div style={{ padding: '12px 16px', background: 'var(--chip-urgent)', border: '1px solid var(--error)', borderRadius: 'var(--radius-input)', color: 'var(--error)', fontSize: '14px' }}>
              {error}
            </div>
          )}

          {mode === 'signin' ? (
            <form onSubmit={handleSignIn} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label className="text-label" style={{ color: 'var(--color-ink)' }}>Username</label>
                <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required placeholder="e.g. john" />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label className="text-label" style={{ color: 'var(--color-ink)' }}>Password</label>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required placeholder="••••••••" />
              </div>
              <button type="submit" className="btn btn-primary btn-lg" style={{ width: '100%', justifyContent: 'center' }} disabled={isSubmitting}>
                {isSubmitting ? <Loader2 size={18} className="spin" style={{ animation: 'spin 1s linear infinite' }} /> : <><LogIn size={18} /> Sign In</>}
              </button>
            </form>
          ) : (
            <form onSubmit={handleSignUp} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label className="text-label" style={{ color: 'var(--color-ink)' }}>Full Name</label>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} required placeholder="e.g. John Doe" />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label className="text-label" style={{ color: 'var(--color-ink)' }}>Email</label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="john@company.com" />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label className="text-label" style={{ color: 'var(--color-ink)' }}>Username</label>
                <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required placeholder="e.g. john" />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label className="text-label" style={{ color: 'var(--color-ink)' }}>Password</label>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required placeholder="At least 8 characters" />
              </div>
              <button type="submit" className="btn btn-primary btn-lg" style={{ width: '100%', justifyContent: 'center' }} disabled={isSubmitting}>
                {isSubmitting ? <Loader2 size={18} className="spin" style={{ animation: 'spin 1s linear infinite' }} /> : <><UserPlus size={18} /> Create Account</>}
              </button>
            </form>
          )}

          {/* Social login buttons */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ flex: 1, height: '1px', background: 'var(--color-rule)' }} />
              <span className="text-caption" style={{ color: 'var(--color-ink-3)', whiteSpace: 'nowrap' }}>
                {mode === 'signin' ? 'or continue with' : 'or sign up with'}
              </span>
              <div style={{ flex: 1, height: '1px', background: 'var(--color-rule)' }} />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <button
                onClick={() => openSSOPopup('google')}
                disabled={isSubmitting}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                  padding: '10px', borderRadius: 'var(--radius-input)', border: '1px solid var(--color-rule-strong)',
                  background: 'var(--color-paper-2)', color: 'var(--color-ink)', cursor: 'pointer',
                  fontSize: '14px', fontWeight: 500, transition: 'all 150ms ease-out', fontFamily: 'var(--font-body)',
                  opacity: isSubmitting ? 0.6 : 1,
                }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
                Google
              </button>
              <button
                onClick={() => openSSOPopup('microsoft')}
                disabled={isSubmitting}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                  padding: '10px', borderRadius: 'var(--radius-input)', border: '1px solid var(--color-rule-strong)',
                  background: 'var(--color-paper-2)', color: 'var(--color-ink)', cursor: 'pointer',
                  fontSize: '14px', fontWeight: 500, transition: 'all 150ms ease-out', fontFamily: 'var(--font-body)',
                  opacity: isSubmitting ? 0.6 : 1,
                }}
              >
                <svg width="18" height="18" viewBox="0 0 21 21"><rect x="1" y="1" width="8.5" height="8.5" fill="#F25022"/><rect x="11.5" y="1" width="8.5" height="8.5" fill="#7FBA00"/><rect x="1" y="11.5" width="8.5" height="8.5" fill="#00A4EF"/><rect x="11.5" y="11.5" width="8.5" height="8.5" fill="#FFB900"/></svg>
                Microsoft
              </button>
            </div>
          </div>

          <div style={{ textAlign: 'center' }}>
            <p className="text-body" style={{ color: 'var(--color-ink-3)', fontSize: '14px' }}>
              {mode === 'signin' ? (
                <>Don't have an account? <button onClick={toggleMode} style={{ background: 'none', border: 'none', color: 'var(--color-accent)', cursor: 'pointer', fontSize: '14px', fontWeight: 500, padding: 0 }}>Sign up</button></>
              ) : (
                <>Already have an account? <button onClick={toggleMode} style={{ background: 'none', border: 'none', color: 'var(--color-accent)', cursor: 'pointer', fontSize: '14px', fontWeight: 500, padding: 0 }}>Sign in</button></>
              )}
            </p>
          </div>

          {/* The old "Demo: admin / admin123" hint was removed: it was wrong on
              any real deployment (the admin user is seeded from the
              ADMIN_PASSWORD env var, see backend/auth/models.py), and printing
              working credentials on a public login page is not something to
              ship regardless. */}
        </div>
      </div>

      <div className="auth-hero-side">
        {mode === 'signin' ? (
          <div style={{ maxWidth: '400px', display: 'flex', flexDirection: 'column', gap: '24px', textAlign: 'center' }}>
            <div style={{ width: '72px', height: '72px', borderRadius: 'var(--radius-panel)', background: 'var(--surface-2)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto' }}>
              <Zap size={36} style={{ color: 'var(--brand-500)' }} />
            </div>
            <h1 style={{ color: 'var(--text-1)', fontSize: '36px' }}>Clear the Noise.<br />Focus on What Matters.</h1>
            <p style={{ color: 'var(--text-2)', fontSize: '16px', lineHeight: 1.6 }}>
              Clutsch aggregates your emails, messages, and tasks, then uses AI to rank them by urgency. 
              Stop context-switching. Start doing your best work.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', alignItems: 'center', marginTop: '8px' }}>
              {['Connect Gmail, Slack, Jira & more', 'AI-powered urgency scoring', 'Enterprise-grade privacy'].map((item, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-2)', fontSize: '14px' }}>
                  <div style={{ width: '20px', height: '20px', borderRadius: 'var(--radius-pill)', background: 'var(--surface-3)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <ArrowRight size={12} style={{ color: 'var(--brand-500)' }} />
                  </div>
                  {item}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ maxWidth: '400px', display: 'flex', flexDirection: 'column', gap: '24px', textAlign: 'center' }}>
            <div style={{ width: '72px', height: '72px', borderRadius: 'var(--radius-panel)', background: 'var(--surface-2)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto' }}>
              <UserPlus size={36} style={{ color: 'var(--brand-500)' }} />
            </div>
            <h1 style={{ color: 'var(--text-1)', fontSize: '36px' }}>Start Your Free Trial.<br />No Credit Card Needed.</h1>
            <p style={{ color: 'var(--text-2)', fontSize: '16px', lineHeight: 1.6 }}>
              Join thousands of professionals who use Clutsch to cut through the noise. 
              Set up in under 2 minutes — connect your tools and let AI do the sorting.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', alignItems: 'center', marginTop: '8px' }}>
              {['14-day free trial, full access to Pro', 'Connect up to 6 integrations', 'Cancel anytime, no questions asked'].map((item, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-2)', fontSize: '14px' }}>
                  <div style={{ width: '20px', height: '20px', borderRadius: 'var(--radius-pill)', background: 'var(--surface-3)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <CheckCircle2 size={12} style={{ color: 'var(--brand-500)' }} />
                  </div>
                  {item}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Login;