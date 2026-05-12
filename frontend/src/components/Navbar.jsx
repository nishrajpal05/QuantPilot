import { Link, useLocation, useNavigate } from 'react-router-dom';
import useAuthStore from '../store/auth';

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const isActive = (path) => location.pathname === path ? 'active' : '';

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-logo">
        <div className="logo-mark">Q</div>
        Quant<span className="logo-accent">Pilot</span>
      </Link>

      <div className="navbar-nav">
        <Link to="/" className={`nav-link ${isActive('/')}`}>Backtest</Link>
        <Link to="/dashboard" className={`nav-link ${isActive('/dashboard')}`}>History</Link>

        {user && (
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            color: 'var(--text-dim)',
            padding: '0 8px',
          }}>
            {user.email?.split('@')[0]}
          </span>
        )}

        <button className="nav-btn-logout" onClick={handleLogout}>
          Sign Out
        </button>
      </div>
    </nav>
  );
}