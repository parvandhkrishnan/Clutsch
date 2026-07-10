import React, { useState, useEffect } from 'react';
import { AlertCircle, X } from 'lucide-react';

const ErrorBanner = () => {
  const [error, setError] = useState(null);

  useEffect(() => {
    const handleGlobalError = (event) => {
      if (event.detail && event.detail.status === 429) {
        setError({
          message: event.detail.message || 'System is currently busy. Please wait a moment before trying again.',
          type: 'rate-limit'
        });
      }
    };

    window.addEventListener('api-error', handleGlobalError);
    return () => window.removeEventListener('api-error', handleGlobalError);
  }, []);

  if (!error) return null;

  return (
    <div className="error-banner rate-limit" role="alert" aria-live="polite">
      <div className="error-content">
        <AlertCircle size={20} aria-hidden="true" />
        <span>{error.message}</span>
      </div>
      <button className="close-btn" onClick={() => setError(null)} aria-label="Dismiss notification">
        <X size={18} aria-hidden="true" />
      </button>
    </div>
  );
};

export default ErrorBanner;
