import { useState, useEffect, useCallback } from 'react'
import { fetchMarketplace, cloneStrategy } from '../api/marketplace'

const TAGS = ['momentum', 'mean-reversion', 'breakout', 'rsi', 'macd', 'sma', 'volatility']

export default function Marketplace() {
  const [strategies, setStrategies] = useState([])
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState(null)
  const [search,     setSearch]     = useState('')
  const [activeTag,  setActiveTag]  = useState('')
  const [cloning,    setCloning]    = useState(null)
  const [cloned,     setCloned]     = useState(new Set())

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (search)    params.search = search
      if (activeTag) params.tag    = activeTag
      const data = await fetchMarketplace(params)
      setStrategies(data.strategies ?? data ?? [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [search, activeTag])

  useEffect(() => { load() }, [load])

  const handleClone = async (id) => {
    setCloning(id)
    try {
      await cloneStrategy(id)
      setCloned(prev => new Set([...prev, id]))
    } catch (e) {
      alert('Clone failed: ' + e.message)
    } finally {
      setCloning(null)
    }
  }

  const ReturnBadge = ({ value }) => {
    const n    = parseFloat(value)
    const pos  = n >= 0
    return (
      <span style={{ color: pos ? '#4ade80' : '#f87171', fontFamily: "'JetBrains Mono', monospace", fontSize: 13, fontWeight: 600 }}>
        {pos ? '+' : ''}{n?.toFixed(1)}%
      </span>
    )
  }

  return (
    <div className="mp-page">
      {/* Header */}
      <div className="mp-header">
        <div>
          <h1 className="mp-title">Strategy Marketplace</h1>
          <p className="mp-sub">Browse community strategies · Clone and backtest instantly</p>
        </div>
        <div className="mp-search-wrap">
          <input
            className="mp-search"
            placeholder="Search strategies…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Tag filter */}
      <div className="mp-tags">
        <button className={`mp-tag ${activeTag === '' ? 'mp-tag--active' : ''}`} onClick={() => setActiveTag('')}>All</button>
        {TAGS.map(t => (
          <button
            key={t}
            className={`mp-tag ${activeTag === t ? 'mp-tag--active' : ''}`}
            onClick={() => setActiveTag(activeTag === t ? '' : t)}
          >{t}</button>
        ))}
      </div>

      {/* Content */}
      {loading && <div className="mp-state">Loading strategies…</div>}
      {error   && <div className="mp-state mp-state--error">⚠ {error}</div>}

      {!loading && !error && (
        <div className="mp-grid">
          {strategies.length === 0 && (
            <div className="mp-empty">No strategies found. Try a different search.</div>
          )}
          {strategies.map(s => (
            <div key={s.id} className="mp-card">
              <div className="mp-card__top">
                <span className="mp-card__title">{s.title}</span>
                <span className="mp-card__clones">{s.clones ?? 0} clones</span>
              </div>

              {s.description && (
                <p className="mp-card__desc">{s.description}</p>
              )}

              {s.tags?.length > 0 && (
                <div className="mp-card__tags">
                  {s.tags.map(t => <span key={t} className="mp-card__tag">{t}</span>)}
                </div>
              )}

              <div className="mp-card__stats">
                {s.avg_return !== null && s.avg_return !== undefined && (
                  <div className="mp-stat">
                    <span className="mp-stat__label">Avg Return</span>
                    <ReturnBadge value={s.avg_return} />
                  </div>
                )}
                {s.avg_sharpe !== null && s.avg_sharpe !== undefined && (
                  <div className="mp-stat">
                    <span className="mp-stat__label">Avg Sharpe</span>
                    <span className="mp-stat__val">{parseFloat(s.avg_sharpe).toFixed(2)}</span>
                  </div>
                )}
              </div>

              <div className="mp-card__footer">
                <span className="mp-card__author">by {s.author ?? 'anonymous'}</span>
                <button
                  className={`mp-clone-btn ${cloned.has(s.id) ? 'mp-clone-btn--done' : ''}`}
                  onClick={() => handleClone(s.id)}
                  disabled={cloning === s.id || cloned.has(s.id)}
                >
                  {cloning === s.id ? 'Cloning…' : cloned.has(s.id) ? '✓ Cloned' : 'Clone'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <style>{`
        .mp-page { max-width: 1100px; margin: 0 auto; padding: 32px 20px; }
        .mp-header { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; margin-bottom: 24px; }
        .mp-title { font-size: 22px; font-weight: 700; color: #f1f5f9; margin: 0; }
        .mp-sub   { font-size: 13px; color: #475569; margin: 4px 0 0; }
        .mp-search-wrap { flex-shrink: 0; }
        .mp-search {
          background: rgba(255,255,255,0.05);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 8px;
          padding: 8px 14px;
          font-size: 13px;
          color: #e2e8f0;
          outline: none;
          width: 240px;
          transition: border-color 0.2s;
        }
        .mp-search:focus { border-color: rgba(99,102,241,0.6); }
        .mp-search::placeholder { color: #334155; }

        .mp-tags { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 24px; }
        .mp-tag {
          padding: 4px 12px;
          border-radius: 20px;
          font-size: 11px;
          font-weight: 500;
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.08);
          color: #64748b;
          cursor: pointer;
          transition: all 0.15s;
        }
        .mp-tag:hover { border-color: rgba(99,102,241,0.4); color: #a5b4fc; }
        .mp-tag--active { background: rgba(99,102,241,0.15); border-color: rgba(99,102,241,0.5); color: #a5b4fc; }

        .mp-state { padding: 48px; text-align: center; color: #475569; font-size: 14px; }
        .mp-state--error { color: #f87171; }
        .mp-empty { grid-column: 1/-1; padding: 48px; text-align: center; color: #475569; }

        .mp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }

        .mp-card {
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 12px;
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 10px;
          transition: border-color 0.2s, transform 0.2s;
        }
        .mp-card:hover { border-color: rgba(99,102,241,0.35); transform: translateY(-1px); }

        .mp-card__top { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
        .mp-card__title { font-size: 14px; font-weight: 600; color: #e2e8f0; line-height: 1.3; }
        .mp-card__clones { font-size: 10px; color: #334155; white-space: nowrap; flex-shrink: 0; }
        .mp-card__desc { font-size: 12px; color: #64748b; line-height: 1.5; margin: 0; }

        .mp-card__tags { display: flex; gap: 6px; flex-wrap: wrap; }
        .mp-card__tag { font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em; padding: 2px 7px; border-radius: 4px; background: rgba(99,102,241,0.1); color: #818cf8; border: 1px solid rgba(99,102,241,0.2); }

        .mp-card__stats { display: flex; gap: 20px; }
        .mp-stat { display: flex; flex-direction: column; gap: 2px; }
        .mp-stat__label { font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em; color: #475569; }
        .mp-stat__val { font-size: 13px; font-weight: 600; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; }

        .mp-card__footer { display: flex; justify-content: space-between; align-items: center; margin-top: auto; }
        .mp-card__author { font-size: 11px; color: #334155; }

        .mp-clone-btn {
          padding: 6px 16px;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 600;
          background: rgba(99,102,241,0.15);
          border: 1px solid rgba(99,102,241,0.4);
          color: #a5b4fc;
          cursor: pointer;
          transition: all 0.15s;
        }
        .mp-clone-btn:hover:not(:disabled) { background: rgba(99,102,241,0.3); }
        .mp-clone-btn:disabled { opacity: 0.5; cursor: default; }
        .mp-clone-btn--done { background: rgba(34,197,94,0.1); border-color: rgba(34,197,94,0.3); color: #4ade80; }
      `}</style>
    </div>
  )
}
