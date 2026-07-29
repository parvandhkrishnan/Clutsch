// Empty by default: frontend and backend served from the same origin
// (local dev via Vite proxy, or a single combined deployment). Set
// VITE_API_BASE_URL at build time when the backend is hosted separately
// (e.g. https://clutsch-backend.onrender.com).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

export const request = async (endpoint, options = {}) => {
  const token = localStorage.getItem('token');
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers,
  };

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

    if (response.status === 429) {
      // Handle rate limiting globally
      const errorData = await response.json();
      const error = new ApiError(errorData.detail || 'Too many requests. Please try again later.', 429, errorData);
      window.dispatchEvent(new CustomEvent('api-error', { detail: error }));
      throw error;
    }

    if (response.status === 401) {
      // In a real app, this is where you'd trigger a refresh token flow
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });

          if (refreshRes.ok) {
            const data = await refreshRes.json();
            if (data.access_token) {
              localStorage.setItem('token', data.access_token);
              // Retry the original request
              return request(endpoint, options);
            }
          }
        } catch (e) {
          console.error("Token refresh failed", e);
        }
      }

      // If refresh fails or no refresh token, logout
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      window.location.hash = '#/login';
      throw new ApiError('Unauthorized', 401);
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(errorData.detail || 'An error occurred', response.status, errorData);
    }

    // Some endpoints might return empty response (like DELETE or 204)
    if (response.status === 204) return null;
    
    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(error.message || 'Network error', 500);
  }
};

export default {
  get: (endpoint, options) => request(endpoint, { ...options, method: 'GET' }),
  post: (endpoint, body, options) => request(endpoint, { ...options, method: 'POST', body: JSON.stringify(body) }),
  put: (endpoint, body, options) => request(endpoint, { ...options, method: 'PUT', body: JSON.stringify(body) }),
  delete: (endpoint, options) => request(endpoint, { ...options, method: 'DELETE' }),
};
