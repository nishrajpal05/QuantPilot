import { useState, useEffect } from 'react';
import { dataAPI } from '../api/client';

const EXAMPLE_STRATEGIES = [
  'Buy RELIANCE when RSI < 30, sell when RSI > 70',
  'Buy when 20-day SMA crosses above 50-day SMA, sell when it crosses below',
  'Enter long when Bollinger Band lower touch occurs, exit at upper band',
  'Buy on breakout above 52-week high, stop loss at 5% below entry',
];

export default function ChatInput({ onSubmit, loading }) {
  const [prompt, setPrompt] = useState('');
  const [symbol, setSymbol] = useState('RELIANCE');
  const [startDate, setStartDate] = useState('2020-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');
  const [capital, setCapital] = useState('100000');
  const [symbols, setSymbols] = useState([]);
  const [symLoading, setSymLoading] = useState(true);

  useEffect(() => {
    let active = true;
    dataAPI.symbols()
      .then((r) => {
        if (active) setSymbols(Array.isArray(r.data) ? r.data : r.data?.symbols || []);
      })
      .catch(() => {
        if (active) setSymbols(['RELIANCE', 'INFY', 'TCS', 'HDFCBANK', 'ICICIBANK', 'NIFTY 50']);
      })
      .finally(() => {
        if (active) setSymLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!prompt.trim() || loading) return;
    onSubmit({ prompt: prompt.trim(), symbol, start_date: startDate, end_date: endDate, initial_capital: parseFloat(capital) });
  };

  const fillExample = (ex) => setPrompt(ex);

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Strategy textarea */}
      <div className="form-group">
        <label className="form-label">Strategy (Natural Language)</label>
        <textarea
          className="form-input form-textarea"
          placeholder="Describe your trading strategy in plain English…"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          required
          disabled={loading}
        />
        {/* Example chips */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
          {EXAMPLE_STRATEGIES.map((ex, i) => (
            <button
              key={i}
              type="button"
              onClick={() => fillExample(ex)}
              disabled={loading}
              style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 2,
                color: 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
                fontSize: 10,
                padding: '3px 8px',
                cursor: 'pointer',
                transition: 'all var(--transition)',
                lineHeight: 1.4,
                textAlign: 'left',
              }}
              onMouseEnter={(e) => { e.target.style.color = 'var(--green)'; e.target.style.borderColor = 'var(--green-dim)'; }}
              onMouseLeave={(e) => { e.target.style.color = 'var(--text-muted)'; e.target.style.borderColor = 'var(--border)'; }}
            >
              {ex.slice(0, 40)}…
            </button>
          ))}
        </div>
      </div>

      {/* Symbol */}
      <div className="form-group">
        <label className="form-label">Symbol</label>
        {symLoading ? (
          <input className="form-input" value="Loading symbols…" disabled />
        ) : symbols.length > 0 ? (
          <select
            className="form-input form-select"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            disabled={loading}
          >
            {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        ) : (
          <input
            className="form-input"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="e.g. RELIANCE"
            disabled={loading}
          />
        )}
      </div>

      {/* Date range */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div className="form-group">
          <label className="form-label">Start Date</label>
          <input
            type="date"
            className="form-input"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            required
            disabled={loading}
            style={{ colorScheme: 'dark' }}
          />
        </div>
        <div className="form-group">
          <label className="form-label">End Date</label>
          <input
            type="date"
            className="form-input"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            required
            disabled={loading}
            style={{ colorScheme: 'dark' }}
          />
        </div>
      </div>

      {/* Capital */}
      <div className="form-group">
        <label className="form-label">Initial Capital (₹)</label>
        <input
          type="number"
          className="form-input"
          value={capital}
          onChange={(e) => setCapital(e.target.value)}
          min="1000"
          step="1000"
          required
          disabled={loading}
          placeholder="100000"
        />
      </div>

      <button
        type="submit"
        className="btn btn-primary btn-lg btn-full"
        disabled={loading || !prompt.trim()}
        style={{ marginTop: 4 }}
      >
        {loading
          ? <><span className="spinner" /> Running Backtest…</>
          : '▶ Run Backtest'}
      </button>
    </form>
  );
}
