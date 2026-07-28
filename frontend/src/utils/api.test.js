import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from './api';

// Mock fetch
global.fetch = vi.fn();

// Mock window.location
const originalLocation = window.location;
delete window.location;
window.location = { ...originalLocation, href: '', hash: '' };

describe('API Utility', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.location.href = '';
    window.location.hash = '';
  });

  it('should include Authorization header if token exists', async () => {
    localStorage.setItem('token', 'fake-token');
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ success: true }),
    });

    await api.get('/test');

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/test'),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer fake-token',
        }),
      })
    );
  });

  it('should handle 401 and attempt token refresh', async () => {
    localStorage.setItem('token', 'expired-token');
    localStorage.setItem('refresh_token', 'valid-refresh-token');

    // First call returns 401
    fetch.mockResolvedValueOnce({
      status: 401,
      ok: false,
      json: async () => ({ detail: 'Unauthorized' }),
    });

    // Refresh call returns new token
    fetch.mockResolvedValueOnce({
      status: 200,
      ok: true,
      json: async () => ({ access_token: 'new-token' }),
    });

    // Retry call returns success
    fetch.mockResolvedValueOnce({
      status: 200,
      ok: true,
      json: async () => ({ success: true }),
    });

    const result = await api.get('/test');

    expect(result).toEqual({ success: true });
    expect(localStorage.getItem('token')).toBe('new-token');
    expect(fetch).toHaveBeenCalledTimes(3);
    
    // Check refresh call
    expect(fetch).toHaveBeenNthCalledWith(2, 
      expect.stringContaining('/auth/refresh'),
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: 'valid-refresh-token' })
      })
    );
  });

  it('should handle 401 and redirect to login if refresh fails', async () => {
    localStorage.setItem('token', 'expired-token');
    localStorage.setItem('refresh_token', 'invalid-refresh-token');

    // First call returns 401
    fetch.mockResolvedValueOnce({
      status: 401,
      ok: false,
      json: async () => ({ detail: 'Unauthorized' }),
    });

    // Refresh call fails
    fetch.mockResolvedValueOnce({
      status: 400,
      ok: false,
      json: async () => ({ detail: 'Bad Request' }),
    });

    await expect(api.get('/test')).rejects.toThrow('Unauthorized');

    // App.jsx uses HashRouter — navigation happens via the URL hash, not
    // window.location.href/pathname.
    expect(window.location.hash).toBe('#/login');
    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });

  it('should handle 401 and redirect to login if no refresh token exists', async () => {
    localStorage.setItem('token', 'expired-token');

    // First call returns 401
    fetch.mockResolvedValueOnce({
      status: 401,
      ok: false,
      json: async () => ({ detail: 'Unauthorized' }),
    });

    await expect(api.get('/test')).rejects.toThrow('Unauthorized');

    expect(window.location.hash).toBe('#/login');
    expect(localStorage.getItem('token')).toBeNull();
  });
  
  it('should handle 429 rate limiting', async () => {
      fetch.mockResolvedValueOnce({
          status: 429,
          ok: false,
          json: async () => ({ detail: 'Rate limit exceeded' }),
      });
      
      const dispatchSpy = vi.spyOn(window, 'dispatchEvent');
      
      await expect(api.get('/test')).rejects.toThrow('Rate limit exceeded');
      expect(dispatchSpy).toHaveBeenCalledWith(expect.objectContaining({
          type: 'api-error'
      }));
  });
});
