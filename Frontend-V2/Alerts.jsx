import { useState, useEffect } from 'react'
import { createAlert, fetchAlerts, deleteAlert } from '../api/marketplace'

const TYPE_LABELS = {
  email:   { icon: '✉', label: 'Email',   placeholder: 'you@example.com' },
  webhook: { icon: '⬡', label: 'Webhook', placeholder: 'https://hooks.example.com/…' },
}

export default function Alerts() {
  const [alerts,      setAlerts]      = useState([])
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState(null)

  // Form state
  const [strategyId,  setStrategyId]  = useState('')
  const [alertType,   setAlertType]   = useState('email')
  const [destination, setDestination] = useState('')
  const [saving,      setSaving]      = useState(false)
  const [formError,   setFormError]   = useState(null)

  useEffect(() => { loadAlerts() }, [])

  const loadAlerts = async () => {
    setLoading(true)
    try {
      const data = await fetchAlerts()
      setAlerts(data.alerts ?? data ?? [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    if (!destination.trim()) { setFormError('Destination is required'); return }
    setSaving(true)
    setFormError(null)
    try {
      const created = await createAlert(strategyId || null, alertType, destination)
      setAlerts(prev => [created, ...prev])
      setDestination('')
      setStrategyId('')
    } catch (e) {
      setFormError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id) => {
    try {
      await deleteAlert(id)
      setAlerts(prev => prev.filter(a => a.id !== id))
    } catch (e) {
      alert('Delete failed: ' + e.message)
    }
  }

  return (
    <div className="al-page">
      <div className="al-header">
        <h1 className="al-title">Alert Configuration</h1>
        <p className="al-sub">Get notified when your strategies generate buy/sell signals</p>
      </div>

      {/* Create form */}
      <div className="al-panel">
        <h2 className="al-panel__title">New Alert</h2>

        {/* Type selector */}
        <div className="al-type-row">
          {Object.entries(TYPE_LABELS).map(([type, meta]) => (
            <button
              key={type}
              className={`al-type-btn ${alertType === type ? 'al-type-btn--active' : ''}`}
              onClick={() => { setAlertType(type); setDestination('') }}
            >
              <span className="al-type-btn__icon">{meta.icon}</span>
              {meta.label}
            </button>
          ))}
        </div>

        <div className="al-form-grid">
          <label className="al-label">
            Strategy ID <span className="al-optional">(optional — leave blank for all)</span>
            <input
              className="al-input"
              placeholder="UUID from your backtest history"
              value={strategyId}
              onChange={e => setStrategyId(e.target.value)}
            />
          </label>

          <label className="al-label">
            {TYPE_LABELS[alertType].label} Destination
            <input
              className="al-input"
              type={alertType === 'email' ? 'email' : 'url'}
              placeholder={TYPE_LABELS[alertType].placeholder}
              value={destination}
              onChange={e => setDestination(e.target.value)}
            />
          </label>
        </div>

        {alertType === 'webhook' && (
          <div className="al-webhook-hint">
            <span className="al-webhook-hint__icon">ℹ</span>
            Webhook will receive a POST with JSON payload: <code>{'{ strategy_id, symbol, signal, price, timestamp }'}</code>
          </div>
        )}

        {formError && <p className="al-form-error">{formError}</p>}

        <button className="al-create-btn" onClick={handleCreate} disabled={saving}>
          {saving ? 'Creating…' : `Create ${TYPE_LABELS[alertType].label} Alert`}
        </button>
      </div>

      {/* Existing alerts */}
      <div className="al-panel">
        <h2 className="al-panel__title">
          Active Alerts
          {alerts.length > 0 && <span className="al-badge">{alerts.length}</span>}
        </h2>

        {loading && <p className="al-state">Loading…</p>}
        {error   && <p className="al-state al-state--error">⚠ {error}</p>}

        {!loading && !error && alerts.length === 0 && (
          <p className="al-state">No alerts configured yet. Create one above.</p>
        )}

        {!loading && alerts.length > 0 && (
          <div className="al-list">
            {alerts.map(a => (
              <div key={a.id} className={`al-item ${!a.active ? 'al-item--inactive' : ''}`}>
                <div className="al-item__icon">
                  {a.type === 'email' ? '✉' : '⬡'}
                </div>
                <div className="al-item__info">
                  <span className="al-item__dest">{a.destination}</span>
                  <span className="al-item__meta">
                    {a.type.toUpperCase()}
                    {a.strategy_id ? ` · strategy ${a.strategy_id.slice(0, 8)}…` : ' · all strategies'}
                    {!a.active && <span className="al-item__inactive-tag"> · inactive</span>}
                  </span>
                </div>
                <button className="al-delete-btn" onClick={() => handleDelete(a.id)} title="Delete alert">
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <style>{`
        .al-page { max-width: 700px; margin: 0 auto; padding: 32px 20px; display: flex; flex-direction: column; gap: 20px; }
        .al-header { }
        .al-title { font-size: 22px; font-weight: 700; color: #f1f5f9; margin: 0; }
        .al-sub   { font-size: 13px; color: #475569; margin: 4px 0 0; }

        .al-panel { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 14px; }
        .al-panel__title { font-size: 13px; font-weight: 600; color: #e2e8f0; margin: 0; display: flex; align-items: center; gap: 8px; }
        .al-badge { background: rgba(99,102,241,0.2); color: #a5b4fc; font-size: 10px; padding: 2px 7px; border-radius: 10px; }

        .al-type-row { display: flex; gap: 10px; }
        .al-type-btn { display: flex; align-items: center; gap: 7px; padding: 8px 18px; border-radius: 8px; font-size: 13px; font-weight: 500; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); color: #64748b; cursor: pointer; transition: all 0.15s; }
        .al-type-btn:hover { border-color: rgba(99,102,241,0.4); color: #a5b4fc; }
        .al-type-btn--active { background: rgba(99,102,241,0.12); border-color: rgba(99,102,241,0.45); color: #a5b4fc; }
        .al-type-btn__icon { font-size: 15px; }

        .al-form-grid { display: flex; flex-direction: column; gap: 12px; }
        .al-label { display: flex; flex-direction: column; gap: 5px; font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
        .al-optional { text-transform: none; font-style: italic; color: #334155; letter-spacing: 0; }
        .al-input { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 7px; padding: 8px 12px; font-size: 13px; color: #e2e8f0; outline: none; transition: border-color 0.2s; }
        .al-input:focus { border-color: rgba(99,102,241,0.5); }
        .al-input::placeholder { color: #334155; }

        .al-webhook-hint { background: rgba(59,130,246,0.07); border: 1px solid rgba(59,130,246,0.2); border-radius: 8px; padding: 10px 14px; font-size: 11px; color: #93c5fd; display: flex; gap: 8px; align-items: flex-start; }
        .al-webhook-hint__icon { flex-shrink: 0; }
        .al-webhook-hint code { font-family: 'JetBrains Mono', monospace; background: rgba(255,255,255,0.07); padding: 1px 5px; border-radius: 4px; }

        .al-form-error { color: #f87171; font-size: 12px; margin: 0; }

        .al-create-btn { padding: 10px 20px; border-radius: 8px; background: rgba(99,102,241,0.2); border: 1px solid rgba(99,102,241,0.5); color: #a5b4fc; font-size: 13px; font-weight: 600; cursor: pointer; align-self: flex-start; transition: all 0.15s; }
        .al-create-btn:hover:not(:disabled) { background: rgba(99,102,241,0.35); }
        .al-create-btn:disabled { opacity: 0.4; cursor: default; }

        .al-state { font-size: 13px; color: #475569; margin: 0; }
        .al-state--error { color: #f87171; }

        .al-list { display: flex; flex-direction: column; gap: 8px; }
        .al-item { display: flex; align-items: center; gap: 12px; padding: 12px 14px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 9px; transition: border-color 0.15s; }
        .al-item:hover { border-color: rgba(255,255,255,0.12); }
        .al-item--inactive { opacity: 0.5; }
        .al-item__icon { font-size: 16px; color: #475569; flex-shrink: 0; width: 22px; text-align: center; }
        .al-item__info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
        .al-item__dest { font-size: 13px; color: #e2e8f0; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .al-item__meta { font-size: 10px; color: #475569; font-family: 'JetBrains Mono', monospace; }
        .al-item__inactive-tag { color: #854d0e; }
        .al-delete-btn { background: none; border: none; color: #334155; cursor: pointer; font-size: 14px; padding: 4px 6px; border-radius: 5px; transition: all 0.15s; flex-shrink: 0; }
        .al-delete-btn:hover { color: #f87171; background: rgba(239,68,68,0.1); }
      `}</style>
    </div>
  )
}
