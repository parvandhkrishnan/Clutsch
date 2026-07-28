import { createContext, useState, useContext, useEffect } from 'react';

// API calls go to the same origin (handled by SPA proxy)
const API_BASE_URL = '';

const AuthContext = createContext(null);

// The backend signs the access token with claims { user_id, tenant_id, role }
// (see backend/auth_routes.py's create_access_token calls), but neither the
// login/register response nor a working "/auth/me" endpoint hands back a
// user object. Decoding the JWT payload client-side is the only way to
// expose the current user's role to the UI without a backend change. This
// is NOT a security boundary — the payload is not signature-verified here —
// it's only used for client-side UX decisions (e.g. hiding the Admin nav
// link); every real admin endpoint enforces the role check server-side.
const decodeTokenPayload = (jwtToken) => {
  try {
    const base64Url = jwtToken.split('.')[1];
    if (!base64Url) return null;
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const json = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + c.charCodeAt(0).toString(16).padStart(2, '0'))
        .join('')
    );
    return JSON.parse(json);
  } catch {
    return null;
  }
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      // In a real app, we might verify the token or fetch user profile here
      // For now, we'll just assume it's valid if present
      localStorage.setItem('token', token);
      const payload = decodeTokenPayload(token);
      if (payload) {
        setUser({ id: payload.user_id, tenant_id: payload.tenant_id, role: payload.role });
      } else {
        setUser(null);
      }
    } else {
      localStorage.removeItem('token');
      setUser(null);
    }
    setLoading(false);
  }, [token]);

  const login = async (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      body: formData,
    });

    if (response.ok) {
      const data = await response.json();
      setToken(data.access_token);
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token);
      }
      return true;
    }
    return false;
  };

  const ssoLogin = async (email, provider) => {
    const response = await fetch(`${API_BASE_URL}/auth/sso/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, provider }),
    });

    if (response.ok) {
      const data = await response.json();
      setToken(data.access_token);
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token);
      }
      return true;
    }
    return false;
  };

  const handleSSOCallback = (accessToken, refreshToken) => {
    setToken(accessToken);
    if (refreshToken) {
      localStorage.setItem('refresh_token', refreshToken);
    }
  };

  const register = async (username, email, password, name = '') => {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password, name }),
    });

    if (response.ok) {
      const data = await response.json();
      setToken(data.access_token);
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token);
      }
      return { success: true };
    }
    const err = await response.json().catch(() => ({ detail: 'Registration failed' }));
    return { success: false, error: err.detail || 'Registration failed' };
  };

  const logout = () => {
    setToken(null);
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, ssoLogin, register, handleSSOCallback, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
