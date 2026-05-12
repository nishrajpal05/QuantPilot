import { create } from 'zustand';

const useAuthStore = create((set) => ({
  token: localStorage.getItem('qp_token') || null,
  user: (() => {
    try { return JSON.parse(localStorage.getItem('qp_user')); } catch { return null; }
  })(),

  login: (token, user) => {
    localStorage.setItem('qp_token', token);
    localStorage.setItem('qp_user', JSON.stringify(user));
    set({ token, user });
  },

  logout: () => {
    localStorage.removeItem('qp_token');
    localStorage.removeItem('qp_user');
    set({ token: null, user: null });
  },

  setUser: (user) => {
    localStorage.setItem('qp_user', JSON.stringify(user));
    set({ user });
  },

  isAuthenticated: () => !!localStorage.getItem('qp_token'),
}));

export default useAuthStore;
