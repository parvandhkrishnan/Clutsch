import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';

const CookieConsent = () => {
  const { token } = useAuth();
  const [show, setShow] = useState(false);
  // Authoritative purpose metadata (id -> { required_for_service, default, ... })
  // fetched from the backend so this banner never relies on a hardcoded,
  // potentially stale copy of CONSENT_PURPOSES.
  const [purposesMeta, setPurposesMeta] = useState(null);

  useEffect(() => {
    const consent = localStorage.getItem('cookie-consent');
    if (!consent) {
      setShow(true);
    }
  }, []);

  // GET /dpdp/notice is a public endpoint (no auth dependency), so it's safe
  // to call before the user logs in — that's how this banner learns which
  // purposes are required_for_service without hardcoding the list.
  useEffect(() => {
    let cancelled = false;
    const fetchPurposes = async () => {
      try {
        const data = await api.get('/dpdp/notice');
        if (!cancelled) setPurposesMeta(data?.purposes || null);
      } catch {
        // Non-critical — if this fails we simply won't be able to sync
        // granular consent to the backend from the banner; localStorage
        // still records the user's accept/decline choice.
      }
    };
    fetchPurposes();
    return () => { cancelled = true; };
  }, []);

  const buildConsentBody = useCallback((acceptAll) => {
    if (!purposesMeta) return null;
    const body = {};
    Object.entries(purposesMeta).forEach(([purposeId, meta]) => {
      // Required-for-service purposes always stay on; only the optional
      // ones (currently marketing_communications, data_sharing_partners)
      // follow the accept/decline choice.
      body[purposeId] = meta.required_for_service ? true : acceptAll;
    });
    return body;
  }, [purposesMeta]);

  const submitConsent = useCallback(async (acceptAll) => {
    // This component is mounted above the route tree in App.jsx, so it can
    // render for anonymous visitors on public pages (landing, login). The
    // real POST /dpdp/consent endpoint requires get_current_active_user, so
    // calling it without a token would always 401 (and api.js treats a 401
    // as a reason to redirect to /login, which would be wrong for an
    // anonymous visitor just dismissing a cookie banner). Skip the network
    // call until a token exists — the choice is still saved to
    // localStorage below and gets synced once the user authenticates.
    if (!token) return;
    const body = buildConsentBody(acceptAll);
    if (!body) return;
    try {
      await api.post('/dpdp/consent', body);
      localStorage.setItem('cookie-consent-synced', 'true');
    } catch {
      // Non-critical for the banner UX — Settings > Privacy & Compliance
      // remains the authoritative place to manage/retry granular consent.
    }
  }, [token, buildConsentBody]);

  // If the visitor accepted/declined anonymously (or an earlier sync
  // attempt failed before purposesMeta had loaded), push that choice to
  // the backend as soon as we have both a token and the purpose list.
  useEffect(() => {
    if (!token) return;
    const consent = localStorage.getItem('cookie-consent');
    const synced = localStorage.getItem('cookie-consent-synced');
    if (consent && !synced) {
      submitConsent(consent === 'accepted');
    }
  }, [token, purposesMeta, submitConsent]);

  const handleAccept = () => {
    localStorage.setItem('cookie-consent', 'accepted');
    localStorage.removeItem('cookie-consent-synced');
    setShow(false);
    submitConsent(true);
  };

  const handleDecline = () => {
    localStorage.setItem('cookie-consent', 'declined');
    localStorage.removeItem('cookie-consent-synced');
    setShow(false);
    submitConsent(false);
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
