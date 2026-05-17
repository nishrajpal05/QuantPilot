import React from 'react'

const STEPS = [
  { label: 'Data',       icon: '⬡' },
  { label: 'Strategy',   icon: '⬡' },
  { label: 'Backtest',   icon: '⬡' },
  { label: 'Risk',       icon: '⬡' },
  { label: 'Compliance', icon: '⬡' },
  { label: 'Audit',      icon: '⬡' },
]

/**
 * AgentProgress
 * @param {number} currentStep  - 0-indexed active step index (-1 = idle, 6 = complete)
 * @param {string} [error]      - if set, renders the error state
 */
export default function AgentProgress({ currentStep = -1, error = null }) {
  if (currentStep === -1) return null

  return (
    <div className="agent-progress">
      <p className="agent-progress__label">
        {error
          ? '⚠ Pipeline error'
          : currentStep >= STEPS.length
          ? '✓ Analysis complete'
          : `Running: ${STEPS[currentStep]?.label}…`}
      </p>

      <div className="agent-progress__track">
        {STEPS.map((step, i) => {
          const done    = i < currentStep
          const active  = i === currentStep && !error
          const failed  = error && i === currentStep

          return (
            <React.Fragment key={step.label}>
              <div className={`ap-node ${done ? 'ap-node--done' : ''} ${active ? 'ap-node--active' : ''} ${failed ? 'ap-node--error' : ''}`}>
                <div className="ap-node__dot">
                  {done   && <span className="ap-node__check">✓</span>}
                  {failed && <span className="ap-node__check">✕</span>}
                </div>
                <span className="ap-node__name">{step.label}</span>
              </div>

              {i < STEPS.length - 1 && (
                <div className={`ap-connector ${done ? 'ap-connector--done' : ''}`} />
              )}
            </React.Fragment>
          )
        })}
      </div>

      {error && <p className="agent-progress__error">{error}</p>}

      <style>{`
        .agent-progress {
          padding: 12px 16px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 10px;
          margin: 16px 0;
        }
        .agent-progress__label {
          font-size: 11px;
          font-family: 'JetBrains Mono', monospace;
          letter-spacing: 0.05em;
          color: #94a3b8;
          margin: 0 0 12px;
          text-transform: uppercase;
        }
        .agent-progress__track {
          display: flex;
          align-items: center;
          gap: 0;
          overflow-x: auto;
          padding-bottom: 2px;
        }
        .ap-node {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 5px;
          flex-shrink: 0;
        }
        .ap-node__dot {
          width: 22px;
          height: 22px;
          border-radius: 50%;
          border: 2px solid rgba(255,255,255,0.15);
          background: rgba(255,255,255,0.04);
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
        }
        .ap-node__check { font-size: 10px; line-height: 1; }
        .ap-node__name {
          font-size: 9px;
          font-family: 'JetBrains Mono', monospace;
          color: #475569;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          white-space: nowrap;
        }
        .ap-node--done .ap-node__dot  { border-color: #22c55e; background: rgba(34,197,94,0.15); color: #22c55e; }
        .ap-node--done .ap-node__name { color: #22c55e; }
        .ap-node--active .ap-node__dot {
          border-color: #3b82f6;
          background: rgba(59,130,246,0.15);
          animation: pulse-dot 1.2s ease-in-out infinite;
        }
        .ap-node--active .ap-node__name { color: #93c5fd; }
        .ap-node--error .ap-node__dot  { border-color: #ef4444; background: rgba(239,68,68,0.15); color: #ef4444; }
        .ap-connector {
          flex: 1;
          min-width: 20px;
          height: 2px;
          background: rgba(255,255,255,0.08);
          margin: 0 4px;
          margin-bottom: 18px;
          transition: background 0.3s ease;
        }
        .ap-connector--done { background: rgba(34,197,94,0.4); }
        .agent-progress__error {
          margin: 8px 0 0;
          font-size: 11px;
          color: #f87171;
          font-family: 'JetBrains Mono', monospace;
        }
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(1.15); }
        }
      `}</style>
    </div>
  )
}
