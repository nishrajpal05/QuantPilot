import { useState } from 'react';
import Navbar from '../components/Navbar';
import ChatInput from '../components/ChatInput';
import StatusPoller from '../components/StatusPoller';
import MetricsGrid from '../components/MetricsGrid';
import EquityCurve from '../components/EquityCurve';
import TradeTable from '../components/TradeTable';
import AuditBadge from '../components/AuditBadge';
import DsrBadge from '../components/DsrBadge';
import { backtestAPI } from '../api/client';

const STATUS_MSG = {
  pending:   'Queued — waiting for worker…',
  running:   'AI is writing and executing your strategy…',
  completed: 'Backtest complete',
  failed:    'Backtest failed',
};

export default function Backtest() {
  const [backtestId, setBacktestId] = useState(null);
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const isRunning = status === 'pending' || status === 'running';

  const handleSubmit = async (data) => {
    setError('');
    setResult(null);
    setBacktestId(null);
    setStatus(null);
    setSubmitting(true);
    try {
      const res = await backtestAPI.create(data);
      setBacktestId(res.data.backtest_id);
      setStatus(res.data.status || 'pending');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start backtest. Is the backend running?');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdate = (data) => {
    setStatus(data.status);
    if (data.status === 'completed' || data.status === 'failed') {
      setResult(data);
    }
  };

  const handleComplete = (data) => {
    setResult(data);
    setStatus(data.status);
  };

  return (
    <div>
      <Navbar />

      <div className="backtest-layout">

        {/* ── Left Sidebar: Input ── */}
        <aside className="backtest-sidebar">
          <div className="card fade-up">
            <div className="card-header">
              <span className="card-title">Strategy Input</span>
              {status && (
                <span className={`badge ${status === 'completed' ? 'badge-green' : status === 'failed' ? 'badge-red' : 'badge-blue'}`}>
                  <span className={`status-dot ${status}`} />
                  {status}
                </span>
              )}
            </div>

            <ChatInput onSubmit={handleSubmit} loading={submitting || isRunning} />

            {/* Status bar */}
            {status && status !== 'completed' && status !== 'failed' && (
              <div style={{ marginTop: 16 }}>
                <div className="poller-bar"><div className="poller-bar-fill" /></div>
                <p style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 11,
                  color: 'var(--text-muted)',
                  marginTop: 8,
                  textAlign: 'center',
                }}>
                  {STATUS_MSG[status] || status}
                </p>
              </div>
            )}

            {error && (
              <div className="alert alert-error" style={{ marginTop: 16 }}>
                <span>⚠</span> {error}
              </div>
            )}
          </div>

          {/* Quick guide */}
          {!backtestId && (
            <div className="card fade-up-2" style={{ marginTop: 16 }}>
              <div className="card-title" style={{ marginBottom: 12 }}>How It Works</div>
              {[
                ['01', 'Describe your strategy in plain English'],
                ['02', 'Groq LLM converts it to vectorbt code'],
                ['03', 'Runs on real NSE/BSE historical data'],
                ['04', 'Risk metrics + DSR overfitting score'],
              ].map(([n, t]) => (
                <div key={n} style={{ display: 'flex', gap: 12, marginBottom: 10, alignItems: 'flex-start' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--green)', minWidth: 20, marginTop: 1 }}>{n}</span>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{t}</span>
                </div>
              ))}
            </div>
          )}
        </aside>

        {/* ── Right: Results ── */}
        <main>
          {/* Poller (invisible) */}
          {backtestId && isRunning && (
            <StatusPoller
              backtestId={backtestId}
              onUpdate={handleUpdate}
              onComplete={handleComplete}
            />
          )}

          {/* Failed */}
          {status === 'failed' && (
            <div className="alert alert-error fade-up">
              <span>✗</span>
              {result?.error_message || 'Strategy execution failed. Check your strategy description and try again.'}
            </div>
          )}

          {/* Completed Results */}
          {status === 'completed' && result && (
            <div className="results-stack">

              {/* Metrics */}
              <div className="fade-up-1">
                <div style={{ marginBottom: 12 }}>
                  <span className="card-title">Performance Metrics</span>
                </div>
                <MetricsGrid result={result} />
              </div>

              {/* DSR */}
              <div className="card fade-up-2">
                <div className="card-header">
                  <span className="card-title">Overfitting Score</span>
                  <span className="badge badge-muted">Deflated Sharpe Ratio</span>
                </div>
                <DsrBadge score={result.dsr_score} />
              </div>

              {/* Equity Curve */}
              <div className="chart-container fade-up-3">
                <div className="card-header">
                  <span className="card-title">Equity Curve</span>
                  {result.equity_curve?.length && (
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)' }}>
                      {result.equity_curve.length} data points
                    </span>
                  )}
                </div>
                <EquityCurve data={result.equity_curve || []} />
              </div>

              {/* Trade Table */}
              <div className="card fade-up-4">
                <div className="card-header">
                  <span className="card-title">Trade Log</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)' }}>
                    {result.trades?.length || 0} trades
                  </span>
                </div>
                <TradeTable trades={result.trades || []} />
              </div>

              {/* Audit */}
              <div className="card fade-up-5">
                <AuditBadge hash={result.audit_hash} />
              </div>

              {/* Share link */}
              <div style={{ textAlign: 'right', paddingBottom: 24 }}>
                <a
                  href={`/backtest/${backtestId}`}
                  className="btn btn-secondary btn-sm"
                  target="_blank"
                  rel="noreferrer"
                >
                  ↗ Shareable Result
                </a>
              </div>
            </div>
          )}

          {/* Empty state */}
          {!backtestId && !result && (
            <div className="empty-state" style={{ minHeight: '60vh' }}>
              <div style={{ fontSize: 48, opacity: 0.1 }}>▶</div>
              <div className="empty-state-title">Run your first backtest</div>
              <div className="empty-state-sub">
                Describe a trading strategy on the left and hit Run Backtest
              </div>
            </div>
          )}

          {/* Waiting skeleton */}
          {isRunning && !result && (
            <div className="card fade-up" style={{ minHeight: 200 }}>
              <div className="loading-state">
                <div className="spinner spinner-lg" />
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-secondary)' }}>
                  {STATUS_MSG[status]}
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)' }}>
                  ID: {backtestId}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
