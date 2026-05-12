import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { backtestAPI } from '../api/client';

const fmtDate = (d) => {
  if (!d) return '—';
  return new Date(d).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
};

const STATUS_BADGE = {
  completed: 'badge-green',
  running:   'badge-blue',
  pending:   'badge-amber',
  failed:    'badge-red',
};

export default function Dashboard() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    backtestAPI.list()
      .then((r) => setHistory(r.data || []))
      .catch(() => setError('Failed to load history.'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <Navbar />

      <div className="page-container" style={{ paddingTop: 28, paddingBottom: 48 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
          <div>
            <h1 style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 700, letterSpacing: -0.5 }}>
              Backtest History
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
              {history.length > 0 ? `${history.length} backtests run` : 'Your past runs appear here'}
            </p>
          </div>
          <Link to="/" className="btn btn-primary btn-sm">+ New Backtest</Link>
        </div>

        <div className="card" style={{ padding: 0 }}>
          {loading && (
            <div className="loading-state">
              <div className="spinner" />
              <span>Loading history…</span>
            </div>
          )}

          {error && (
            <div className="alert alert-error" style={{ margin: 20 }}>
              <span>⚠</span> {error}
            </div>
          )}

          {!loading && !error && history.length === 0 && (
            <div className="empty-state">
              <div className="empty-state-icon">📊</div>
              <div className="empty-state-title">No backtests yet</div>
              <div className="empty-state-sub">Run your first backtest to see results here</div>
              <Link to="/" className="btn btn-primary btn-sm" style={{ marginTop: 8 }}>
                → Run Backtest
              </Link>
            </div>
          )}

          {!loading && history.length > 0 && (
            <>
              {/* Table header */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 100px 120px 120px 40px',
                gap: 16,
                padding: '10px 16px',
                borderBottom: '1px solid var(--border)',
                background: 'var(--bg-surface)',
              }}>
                {['Strategy / Symbol', 'Status', 'Created', 'Return', ''].map((h) => (
                  <span key={h} style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 10,
                    fontWeight: 600,
                    color: 'var(--text-dim)',
                    textTransform: 'uppercase',
                    letterSpacing: 1,
                  }}>{h}</span>
                ))}
              </div>

              {history.map((item) => {
                const ret = item.total_return_pct;
                const retNum = parseFloat(ret);
                return (
                  <Link
                    key={item.id}
                    to={`/backtest/${item.id}`}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 100px 120px 120px 40px',
                      gap: 16,
                      padding: '14px 16px',
                      borderBottom: '1px solid var(--border)',
                      textDecoration: 'none',
                      color: 'inherit',
                      transition: 'background var(--transition)',
                      alignItems: 'center',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-hover)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = ''}
                  >
                    {/* Symbol + prompt */}
                    <div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>
                        {item.symbol || '—'}
                      </div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }} className="truncate">
                        {item.prompt?.slice(0, 60) || '—'}
                      </div>
                    </div>

                    {/* Status */}
                    <div>
                      <span className={`badge ${STATUS_BADGE[item.status] || 'badge-muted'}`}>
                        <span className={`status-dot ${item.status}`} />
                        {item.status}
                      </span>
                    </div>

                    {/* Date */}
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
                      {fmtDate(item.created_at)}
                    </div>

                    {/* Return */}
                    <div style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: 13,
                      fontWeight: 600,
                      color: ret != null ? (retNum >= 0 ? 'var(--green)' : 'var(--red)') : 'var(--text-dim)',
                    }}>
                      {ret != null ? `${retNum >= 0 ? '+' : ''}${retNum.toFixed(2)}%` : '—'}
                    </div>

                    {/* Arrow */}
                    <div style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: 14 }}>›</div>
                  </Link>
                );
              })}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
