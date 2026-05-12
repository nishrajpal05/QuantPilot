import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: BASE_URL,
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
  register: (data) => client.post('/api/v1/auth/register', data),
  login: (data) => client.post('/api/v1/auth/login', data),
  me: () => client.get('/api/v1/auth/me'),
};

// ── Backtest ──────────────────────────────────────────────────
export const backtestAPI = {
  create: (data) => client.post('/api/v1/backtest', data),
  getById: (id) => client.get(`/api/v1/backtest/${id}`),
  list: () => client.get('/api/v1/backtest/list'),
};

// ── Data ──────────────────────────────────────────────────────
export const dataAPI = {
  symbols: () => client.get('/api/v1/data/symbols'),
};

export default client;
