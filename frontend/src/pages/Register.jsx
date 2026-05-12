import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authAPI } from '../api/client';
import useAuthStore from '../store/auth';

export default function Register() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const [form, setForm] = useState({ full_name: '', email: '', password: '', confirm: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (form.password !== form.confirm) {
      setError('Passwords do not match.');
      return;
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    setLoading(true);
    try {
      const res = await authAPI.register({
        full_name: form.full_name,
        email: form.email,
        password: form.password,
      });
      const { access_token } = res.data;
      localStorage.setItem('qp_token', access_token);
      const meRes = await authAPI.me();
      login(access_token, meRes.data);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  return (
    <div className="auth-page">
      <div className="auth-card fade-up">
        <div className="auth-logo">
          <div className="auth-logo-mark">Q</div>
          <div className="auth-title">Create Account</div>
          <div className="auth-subtitle">Start backtesting in seconds</div>
        </div>

        {error && (
          <div className="alert alert-error" style={{ marginBottom: 20 }}>
            <span>⚠</span> {error}
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input
              type="text"
              className="form-input"
              placeholder="Arjun Sharma"
              value={form.full_name}
              onChange={set('full_name')}
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label className="form-label">Email</label>
            <input
              type="email"
              className="form-input"
              placeholder="trader@example.com"
              value={form.email}
              onChange={set('email')}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-input"
              placeholder="Min 8 characters"
              value={form.password}
              onChange={set('password')}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Confirm Password</label>
            <input
              type="password"
              className="form-input"
              placeholder="Repeat password"
              value={form.confirm}
              onChange={set('confirm')}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-lg btn-full"
            disabled={loading}
          >
            {loading ? <><span className="spinner" /> Creating account…</> : '→ Create Account'}
          </button>
        </form>

        <div className="auth-divider" style={{ marginTop: 24 }}>
          Already have an account?{' '}
          <Link to="/login" className="auth-link">Sign in</Link>
        </div>
      </div>
    </div>
  );
}
