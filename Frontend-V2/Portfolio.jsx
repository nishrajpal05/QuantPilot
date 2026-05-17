import { useState } from 'react'
import { analyzePortfolio } from '../api/marketplace'
import CorrelationMatrix from '../components/CorrelationMatrix'

const PRESET_SYMBOLS = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'HINDUNILVR', 'BAJFINANCE', 'KOTAKBANK']

export default function Portfolio() {
  const [symbols,     setSymbols]     = useState(['RELIANCE', 'TCS', 'INFY'])
  const [newSymbol,   setNewSymbol]   = useState('')
  const [startDate,   setStartDate]   = useState('2023-01-01')
  const [endDate,     setEndDate]     = useState(new Date().toISOString().split('T')[0])
  const [result,      setResult]      = useState(null)
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState(null)

  const addSymbol = (sym) => {
    const s = sym.trim().toUpperCase()
    if (s && !symbols.includes(s) && symbols.length < 10) {
      setSymbols(prev => [...prev, s])
    }
    setNewSymbol('')
  }

  const removeSymbol = (sym) => setSymbols(prev => prev.filter(s => s !== sym))

  const handleAnalyze = async () => {
    if (symbols.length < 2) { setError('Add at least 2 symbols'); return }
    setLoading(true)
    setError(null)
    try {
      const data = await analyzePortfolio(symbols, startDate, endDate)
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="pf-page">
      <div className="pf-header">
        <h1 className="pf-title">Portfolio Analytics</h1>
        <p className="pf-sub">Analyze correlation and factor exposure across multiple symbols</p>
      </div>

      {/* Config panel */}
      <div className="pf-panel">
        <h2 className="pf-panel__title">Symbols <span className="pf-panel__hint">max 10</span></h2>

        {/* Presets */}
        <div className="pf-presets">
          {PRESET_SYMBOLS.map(s => (
            <button
              key={s}
              className={`pf-preset ${symbols.includes(s) ? 'pf-preset--active' : ''}`}
              onClick={() => symbols.includes(s) ? removeSymbol(s) : addSymbol(s)}
              disabled={!symbols.includes(s) && symbols.length >= 10}
            >{s}</button>
          ))}
        </div>

        {/* Custom add */}
        <div className="pf-add-row">
          <input
            className="pf-input"
            placeholder="Add symbol (e.g. WIPRO)"
            value={newSymbol}
            onChange={e => setNewSymbol(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addSymbol(newSymbol)}
          />
          <button className="pf-add-btn" onClick={() => addSymbol(newSymbol)}>+ Add</button>
        </div>

        {/* Selected chips */}
        <div className="pf-chips">
          {symbols.map(s => (
            <span key={s} className="pf-chip">
              {s}
              <button className="pf-chip__remove" onClick={() => removeSymbol(s)}>×</button>
            </span>
          ))}
        </div>

        {/* Date range */}
        <div className="pf-dates">
          <label className="pf-label">
            From
            <input type="date" className="pf-input pf-input--date" value={startDate} onChange={e => setStartDate(e.target.value)} />
          </label>
          <label className="pf-label">
            To
            <input type="date" className="pf-input pf-input--date" value={endDate} onChange={e => setEndDate(e.target.value)} />
          </label>
        </div>

        <button className="pf-analyze-btn" onClick={handleAnalyze} disabled={loading || symbols.length < 2}>
          {loading ? 'Analyzing…' : 'Analyze Portfolio'}
        </button>

        {error && <p className="pf-error">{error}</p>}
      </div>

      {/* Results */}
      {result && (
        <div className="pf-results">
          {/* Summary stats */}
          {result.portfolio_stats && (
            <div className="pf-stats-grid">
              {Object.entries(result.portfolio_stats).map(([k, v]) => (
                <div key={k} className="pf-stat-card">
                  <span className="pf-stat-card__label">{k.replace(/_/g, ' ')}</span>
                  <span className="pf-stat-card__val">{typeof v === 'number' ? v.toFixed(3) : v}</span>
                </div>
              ))}
            </div>
          )}

          {/* Correlation heatmap */}
          {result.correlation_matrix && (
            <CorrelationMatrix
              matrix={result.correlation_matrix}
              symbols={result.symbols ?? symbols}
            />
          )}

          {/* Per-symbol returns */}
          {result.individual_returns && (
            <div className="pf-panel">
              <h2 className="pf-panel__title">Individual Performance</h2>
              <table className="pf-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Return</th>
                    <th>Volatility</th>
                    <th>Sharpe</th>
                    <th>Max DD</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(result.individual_returns).map(([sym, stats]) => (
                    <tr key={sym}>
                      <td className="pf-table__sym">{sym}</td>
                      <td style={{ color: stats.return >= 0 ? '#4ade80' : '#f87171' }}>
                        {stats.return >= 0 ? '+' : ''}{(stats.return * 100).toFixed(1)}%
                      </td>
                      <td>{(stats.volatility * 100).toFixed(1)}%</td>
                      <td>{stats.sharpe?.toFixed(2)}</td>
                      <td style={{ color: '#f87171' }}>{(stats.max_drawdown * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <style>{`
        .pf-page { max-width: 900px; margin: 0 auto; padding: 32px 20px; display: flex; flex-direction: column; gap: 20px; }
        .pf-header { }
        .pf-title { font-size: 22px; font-weight: 700; color: #f1f5f9; margin: 0; }
        .pf-sub   { font-size: 13px; color: #475569; margin: 4px 0 0; }

        .pf-panel { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 14px; }
        .pf-panel__title { font-size: 13px; font-weight: 600; color: #e2e8f0; margin: 0; }
        .pf-panel__hint  { font-weight: 400; color: #475569; font-size: 11px; }

        .pf-presets { display: flex; gap: 8px; flex-wrap: wrap; }
        .pf-preset { padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 500; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); color: #64748b; cursor: pointer; transition: all 0.15s; }
        .pf-preset:hover:not(:disabled) { border-color: rgba(99,102,241,0.4); color: #a5b4fc; }
        .pf-preset--active { background: rgba(99,102,241,0.12); border-color: rgba(99,102,241,0.4); color: #a5b4fc; }
        .pf-preset:disabled { opacity: 0.3; cursor: default; }

        .pf-add-row { display: flex; gap: 8px; }
        .pf-input { flex: 1; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 7px; padding: 7px 12px; font-size: 13px; color: #e2e8f0; outline: none; }
        .pf-input:focus { border-color: rgba(99,102,241,0.5); }
        .pf-input::placeholder { color: #334155; }
        .pf-input--date { flex: none; width: auto; }
        .pf-add-btn { padding: 7px 14px; border-radius: 7px; background: rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.35); color: #a5b4fc; font-size: 12px; font-weight: 600; cursor: pointer; white-space: nowrap; }
        .pf-add-btn:hover { background: rgba(99,102,241,0.25); }

        .pf-chips { display: flex; gap: 8px; flex-wrap: wrap; }
        .pf-chip { display: flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 6px; background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.25); font-size: 11px; color: #a5b4fc; font-weight: 600; }
        .pf-chip__remove { background: none; border: none; color: #475569; cursor: pointer; font-size: 14px; line-height: 1; padding: 0; }
        .pf-chip__remove:hover { color: #f87171; }

        .pf-dates { display: flex; gap: 16px; flex-wrap: wrap; }
        .pf-label { display: flex; flex-direction: column; gap: 5px; font-size: 11px; color: #64748b; }

        .pf-analyze-btn { padding: 10px 24px; border-radius: 8px; background: rgba(99,102,241,0.2); border: 1px solid rgba(99,102,241,0.5); color: #a5b4fc; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.15s; align-self: flex-start; }
        .pf-analyze-btn:hover:not(:disabled) { background: rgba(99,102,241,0.35); }
        .pf-analyze-btn:disabled { opacity: 0.4; cursor: default; }
        .pf-error { color: #f87171; font-size: 12px; margin: 0; }

        .pf-results { display: flex; flex-direction: column; gap: 20px; }
        .pf-stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
        .pf-stat-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 10px; padding: 12px; }
        .pf-stat-card__label { font-size: 9px; text-transform: uppercase; letter-spacing: 0.08em; color: #475569; display: block; margin-bottom: 4px; }
        .pf-stat-card__val   { font-size: 16px; font-weight: 700; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; }

        .pf-table { width: 100%; border-collapse: collapse; font-size: 12px; }
        .pf-table th { text-align: left; padding: 8px 12px; color: #475569; font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; border-bottom: 1px solid rgba(255,255,255,0.06); }
        .pf-table td { padding: 10px 12px; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.04); font-family: 'JetBrains Mono', monospace; font-size: 12px; }
        .pf-table__sym { color: #e2e8f0; font-weight: 600; }
        .pf-table tr:last-child td { border-bottom: none; }
        .pf-table tr:hover td { background: rgba(255,255,255,0.02); }
      `}</style>
    </div>
  )
}
