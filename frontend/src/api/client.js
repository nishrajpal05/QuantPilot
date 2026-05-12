import axios from 'axios';

const API_ORIGIN = import.meta.env.VITE_API_URL;

if (!API_ORIGIN) {
  throw new Error('VITE_API_URL is required. Example: http://localhost:8000');
}

const client = axios.create({
  baseURL: `${API_ORIGIN.replace(/\/$/, '')}/api/v1`,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Request: attach JWT ──────────────────────────────────────
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('qp_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response: handle 401 globally ───────────────────────────
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('qp_token');
      localStorage.removeItem('qp_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ── Auth ─────────────────────────────────────────────────────
export const authAPI = {
  register: (data) => client.post('/auth/register', data),
  login: (data) => client.post('/auth/login', data),
  me: () => client.get('/auth/me'),
};

// ── Backtest ──────────────────────────────────────────────────
export const backtestAPI = {
  create: (data) => client.post('/backtest', data),
  getById: (id) => client.get(`/backtest/${id}`),
  list: () => client.get('/backtest/list'),
};

// ── Data ──────────────────────────────────────────────────────
export const dataAPI = {
  symbols: () => client.get('/data/symbols'),
};

export default client;
