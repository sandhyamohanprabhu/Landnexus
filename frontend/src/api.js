// Centralized API Configuration & Client Wrapper
const rawEnvApi = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL : '').trim();

export const API_BASE_URL = rawEnvApi
  ? rawEnvApi.replace(/\/+$/, '')
  : (typeof window !== 'undefined' && (window.location.port === '5173' || window.location.port === '3000') ? 'http://127.0.0.1:8001' : '');

export const EventBus = {
  listeners: new Set(),
  dispatch() {
    this.listeners.forEach(l => {
      try { l(); } catch (_) {}
    });
  },
  subscribe(l) {
    this.listeners.add(l);
    return () => this.listeners.delete(l);
  }
};

export async function api(path, opt = {}) {
  if (!path) throw Error('API endpoint is not configured');
  const t = typeof localStorage !== 'undefined' ? localStorage.getItem('survi_token') : null;
  let headers = { ...(opt.headers || {}) };
  if (!(opt.body instanceof FormData)) headers['Content-Type'] = 'application/json';
  if (t && t !== 'undefined' && t !== 'null') headers.Authorization = 'Bearer ' + t;
  let r;
  try {
    const url = path.startsWith('http://') || path.startsWith('https://') ? path : `${API_BASE_URL}${path}`;
    r = await fetch(url, { ...opt, headers });
  } catch (error) {
    throw Error(error.message || 'Unable to reach the backend API. Please check your network and backend server.');
  }
  let j = null;
  const contentType = (r.headers && r.headers.get('content-type')) || '';
  if (contentType.includes('application/json')) {
    try { j = await r.json(); } catch { j = null; }
  } else {
    const text = await r.text().catch(() => '');
    if (text.trim().startsWith('<!DOCTYPE') || text.trim().startsWith('<html')) {
      throw Error(`Backend API endpoint '${path}' was not found (received HTML instead of JSON). If deployed on Vercel, set VITE_API_URL to your live backend URL in Vercel project settings.`);
    }
    try { j = JSON.parse(text); } catch { j = null; }
  }
  if (!r.ok || j === null) {
    const detail = j?.detail || j?.message;
    const message = typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : `Request failed (${r.status})`;
    const error = Error(message);
    error.status = r.status;
    throw error;
  }
  
  if (opt.method && opt.method !== 'GET') {
    EventBus.dispatch();
  }
  return j;
}

api.API = API_BASE_URL;
