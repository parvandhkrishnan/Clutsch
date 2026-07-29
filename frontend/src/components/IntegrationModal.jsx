import { useState, useEffect } from 'react';
import { X, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

const IntegrationModal = ({ isOpen, onClose, integration, onConnectSuccess }) => {
  const [step, setStep] = useState('initial'); // initial, connecting, success, error
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setStep('initial');
      setError(null);
    }
    
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  const handleConnect = async () => {
    setStep('connecting');
    try {
      // Simulate OAuth flow
      await new Promise(resolve => setTimeout(resolve, 2000));
      // In real app: await api.post(`/integrations/${integration.id}/connect`, { ... });
      setStep('success');
      if (onConnectSuccess) onConnectSuccess(integration.id);
    } catch (err) {
      setStep('error');
      setError(err.message || 'Failed to connect');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card integration-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '400px' }}>
        <div className="modal-header">
          <h2>Connect {integration.name}</h2>
          <button className="close-btn" onClick={onClose}><X size={24} /></button>
        </div>
        
        <div className="modal-body" style={{ padding: '40px 20px', textAlign: 'center' }}>
          {step === 'initial' && (
            <div className="connection-initial">
              <div className="integration-icon-large" style={{ 
                width: '80px', 
                height: '80px', 
                backgroundColor: '#f1f5f9', 
                borderRadius: '20px', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                margin: '0 auto 24px'
              }}>
                <integration.icon size={48} color="var(--color-accent)" />
              </div>
              <p style={{ marginBottom: '24px', color: 'var(--color-ink-3)' }}>
                Connect your {integration.name} account to start prioritizing your communications with AI.
              </p>
              <button className="btn btn-primary w-100" onClick={handleConnect} style={{ padding: '12px' }}>
                Authorize {integration.name}
              </button>
            </div>
          )}

          {step === 'connecting' && (
            <div className="connection-loading">
              <Loader2 className="spin" size={64} color="var(--color-accent)" style={{ margin: '0 auto 24px' }} />
              <h3>Connecting to {integration.name}...</h3>
              <p style={{ color: 'var(--color-ink-3)' }}>Please wait while we authorize your account.</p>
            </div>
          )}

          {step === 'success' && (
            <div className="connection-success">
              <CheckCircle2 size={64} color="#10b981" style={{ margin: '0 auto 24px' }} />
              <h3>Connection Successful!</h3>
              <p style={{ marginBottom: '24px', color: 'var(--color-ink-3)' }}>
                Your {integration.name} account is now connected and syncing.
              </p>
              <button className="btn btn-primary w-100" onClick={onClose}>Done</button>
            </div>
          )}

          {step === 'error' && (
            <div className="connection-error">
              <AlertCircle size={64} color="#ef4444" style={{ margin: '0 auto 24px' }} />
              <h3>Connection Failed</h3>
              <p style={{ marginBottom: '24px', color: 'var(--color-ink-3)' }}>{error}</p>
              <button className="btn btn-primary w-100" onClick={handleConnect}>Try Again</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default IntegrationModal;
