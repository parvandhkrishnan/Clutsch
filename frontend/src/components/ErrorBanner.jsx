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
    <div className="error-banner rate-limit">
      <div className="error-content">
        <AlertCircle size={20} />
        <span>{error.message}</span>
      </div>
      <button className="close-btn" onClick={() => setError(null)}>
        <X size={18} />
      </button>
    </div>
  );
};

export default ErrorBanner;
