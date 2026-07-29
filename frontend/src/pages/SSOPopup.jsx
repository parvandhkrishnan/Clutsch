import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Loader2, ExternalLink } from 'lucide-react';

// Empty by default (same-origin); set VITE_API_BASE_URL at build time
// when the backend is hosted separately from the frontend.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const SSOPopup = () => {
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const provider = params.get('provider') || 'google';
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [step, setStep] = useState('email'); // email -> submitting -> done

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email) return;
    setError('');
    setIsSubmitting(true);
    setStep('submitting');

    try {
      const response = await fetch(`${API_BASE_URL}/auth/sso/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, provider }),
      });

      if (response.ok) {
        const data = await response.json();
        // Post success message to opener window
        if (window.opener) {
          window.opener.postMessage({
            type: 'sso-success',
            token: data.access_token,
            refresh_token: data.refresh_token,
          }, '*');
        }
        setStep('done');
        // Close after a brief moment
        setTimeout(() => window.close(), 800);
      } else {
        const err = await response.json().catch(() => ({ detail: 'SSO login failed' }));
        setError(err.detail || 'No account found with that email');
        setStep('email');
      }
    } catch {
      setError('Connection error. Please try again.');
      setStep('email');
    } finally {
      setIsSubmitting(false);
    }
  };

  const providerName = provider === 'google' ? 'Google' : 'Microsoft';
  const providerColor = provider === 'google' ? '#4285F4' : '#00A4EF';
  const providerIcon = provider === 'google' ? (
    <svg width="24" height="24" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
  ) : (
    <svg width="24" height="24" viewBox="0 0 21 21"><rect x="1" y="1" width="8.5" height="8.5" fill="#F25022"/><rect x="11.5" y="1" width="8.5" height="8.5" fill="#7FBA00"/><rect x="1" y="11.5" width="8.5" height="8.5" fill="#00A4EF"/><rect x="11.5" y="11.5" width="8.5" height="8.5" fill="#FFB900"/></svg>
  );

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#0a0a0f',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      padding: '24px',
    }}>
      <div style={{
        width: '100%',
        maxWidth: '400px',
        background: 'rgba(255,255,255,0.04)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '16px',
        padding: '32px',
        textAlign: 'center',
      }}>
        {/* Provider Icon */}
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          background: 'rgba(255,255,255,0.06)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 16px',
        }}>
          {providerIcon}
        </div>

        <h1 style={{ color: '#fff', fontSize: '20px', fontWeight: 600, margin: '0 0 8px' }}>
          Sign in with {providerName}
        </h1>
        <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '14px', margin: '0 0 24px', lineHeight: 1.5 }}>
          Enter the email associated with your {providerName} account to continue.
        </p>

        {step === 'done' ? (
          <div style={{ padding: '20px 0' }}>
            <div style={{
              width: '48px', height: '48px', borderRadius: '50%',
              background: 'rgba(34, 197, 94, 0.15)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 12px',
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M20 6L9 17l-5-5" stroke="#22c55e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <p style={{ color: '#22c55e', fontSize: '15px', fontWeight: 500 }}>Authenticated!</p>
            <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '13px' }}>Closing popup...</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {error && (
              <div style={{
                padding: '10px 14px', background: 'rgba(239,68,68,0.1)',
                border: '1px solid rgba(239,68,68,0.2)', borderRadius: '10px',
                color: '#ef4444', fontSize: '13px', textAlign: 'left',
              }}>
                {error}
              </div>
            )}
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@gmail.com"
              autoFocus
              required
              disabled={isSubmitting}
              style={{
                padding: '12px 16px', borderRadius: '10px',
                border: '1px solid rgba(255,255,255,0.1)',
                background: 'rgba(255,255,255,0.05)',
                color: '#fff', fontSize: '15px',
                outline: 'none', transition: 'border-color 0.15s',
                fontFamily: 'inherit',
                opacity: isSubmitting ? 0.6 : 1,
              }}
              onFocus={(e) => e.target.style.borderColor = providerColor}
              onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
            />
            <button
              type="submit"
              disabled={isSubmitting || !email}
              style={{
                padding: '12px 16px', borderRadius: '10px',
                border: 'none', cursor: isSubmitting || !email ? 'not-allowed' : 'pointer',
                background: providerColor, color: '#fff',
                fontSize: '15px', fontWeight: 600,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                opacity: isSubmitting || !email ? 0.6 : 1,
                transition: 'opacity 0.15s',
                fontFamily: 'inherit',
              }}
            >
              {isSubmitting ? (
                <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Verifying...</>
              ) : (
                <><ExternalLink size={16} /> Continue with {providerName}</>
              )}
            </button>
          </form>
        )}
      </div>

      <p style={{
        color: 'rgba(255,255,255,0.25)', fontSize: '12px', marginTop: '20px',
        textAlign: 'center',
      }}>
        This popup will close automatically after authentication.
      </p>
    </div>
  );
};

export default SSOPopup;