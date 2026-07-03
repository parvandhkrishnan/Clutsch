import React, { useState, useEffect } from 'react';

const CookieConsent = () => {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const consent = localStorage.getItem('cookie-consent');
    if (!consent) {
      setShow(true);
    }
  }, []);

  const handleAccept = () => {
    localStorage.setItem('cookie-consent', 'accepted');
    setShow(false);
  };

  const handleDecline = () => {
    localStorage.setItem('cookie-consent', 'declined');
    setShow(false);
  };

  if (!show) return null;

  return (
    <div className="cookie-consent-banner">
      <div className="cookie-consent-content">
        <p>
          We use cookies to enhance your experience and analyze our traffic. 
          By clicking "Accept", you consent to our use of cookies.
        </p>
        <div className="cookie-consent-buttons">
          <button className="btn btn-secondary" onClick={handleDecline}>Decline</button>
          <button className="btn btn-primary" onClick={handleAccept}>Accept</button>
        </div>
      </div>
    </div>
  );
};

export default CookieConsent;
