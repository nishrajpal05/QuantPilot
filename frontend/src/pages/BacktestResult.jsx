import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import MetricsGrid from '../components/MetricsGrid';
import EquityCurve from '../components/EquityCurve';
import TradeTable from '../components/TradeTable';
import AuditBadge from '../components/AuditBadge';
import DsrBadge from '../components/DsrBadge';
import StatusPoller from '../components/StatusPoller';
import { backtestAPI } from '../api/client';

const fmtDate = (d) => d?.slice(0, 10) || '—';

export default function BacktestResult() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    backtestAPI.getById(id)
      .then((r) => setData(r.data))
      .catch(() => setError('Result not found or you do not have access.'))
      .finally(() => setLoading(false));
  }, [id]);

  const isRunning = data?.status === 'pending' || data?.status === 'running';

  const handleUpdate = (d) => setData(d);
  const handleComplete = (d) => setData(d);

  return (
    <div>
      <Navbar />

      {isRunning && (
        <StatusPoller backtestId={id} onUpdate={handleUpdate} onComplete={handleComplete} />
      )}

      <div className="page-container" style={{ paddingTop: 28, paddingBottom: 48 }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Link to="/dashboard" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 12, textDecoration: 'none' }}>
                ← History
              </Link>
              <span style={{ color: 'var(--border)' }}>·</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-dim)' }}>{id}</span>
            </div>
            <h1 style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 700, letterSpacing: -0.5, marginTop: 8 }}>
              {data?.symbol || '—'} Backtest
            </h1>
            {data && (
              <p style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 4, fontFamily: 'var(--font-mono)' }}>
                {fmtDate(data.start_date)} → {fmtDate(data.end_date)}
                {data.initial_capital && ` · ₹${Number(data.initial_capital).toLocaleString('en-IN')} capital`}
              </p>
            )}
          </div>

          <Link to="/" className="btn btn-secondary btn-sm">+ New Backtest</Link>
        </div>

        {/* Loading */}
        {loading && (
          <div className="loading-state">
            <div className="spinner spinner-lg" />
            <span>Loading result…</span>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="alert alert-error">
            <span>⚠</span> {error}
          </div>
        )}

        {/* In-progress */}
        {!loading && isRunning && (
          <div className="card fade-up" style={{ minHeight: 160 }}>
            <div className="loading-state">
              <div className="spinner spinner-lg" />
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-secondary)' }}>
                Backtest is {data.status}…
              </div>
              <div className="poller-bar" style={{ width: 200 }}>
                <div className="poller-bar-fill" />
              </div>
            </div>
          </div>
        )}

        {/* Strategy prompt */}
        {data?.prompt && (
          <div className="card fade-up" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <span className="card-title">Strategy</span>
            </div>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              "{data.prompt}"
            </p>
          </div>
        )}

        {/* Failed */}
        {data?.status === 'failed' && (
          <div className="alert alert-error fade-up">
            <span>✗</span> {data.error_message || 'Strategy execution failed.'}
          </div>
        )}

        {/* Results */}
        {data?.status === 'completed' && (
          <div className="results-stack">
            <div className="fade-up-1">
              <div style={{ marginBottom: 12 }}>
                <span className="card-title">Performance Metrics</span>
              </div>
              <MetricsGrid result={data} />
            </div>

            <div className="card fade-up-2">
              <div className="card-header">
                <span className="card-title">Overfitting Score</span>
                <span className="badge badge-muted">Deflated Sharpe Ratio</span>
              </div>
              <DsrBadge score={data.dsr_score} />
            </div>

            <div className="chart-container fade-up-3">
              <div className="card-header">
                <span className="card-title">Equity Curve</span>
              </div>
              <EquityCurve data={data.equity_curve || []} />
            </div>

            <div className="card fade-up-4">
              <div className="card-header">
                <span className="card-title">Trade Log</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)' }}>
                  {data.trades?.length || 0} trades
                </span>
              </div>
              <TradeTable trades={data.trades || []} />
            </div>

            <div className="card fade-up-5">
              <AuditBadge hash={data.audit_hash} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
