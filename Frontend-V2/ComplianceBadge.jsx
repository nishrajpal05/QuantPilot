/**
 * ComplianceBadge
 * @param {{
 *   compliant: boolean
 *   issues: string[]
 *   algo_id: string
 *   checked_at: string
 * }} props
 */
export default function ComplianceBadge({ compliant, issues = [], algo_id, checked_at }) {
  if (compliant === undefined) return null

  return (
    <div className={`compliance-badge ${compliant ? 'compliance-badge--ok' : 'compliance-badge--fail'}`}>
      <div className="compliance-badge__header">
        <span className="compliance-badge__icon">{compliant ? '✓' : '⚠'}</span>
        <span className="compliance-badge__status">
          SEBI {compliant ? 'Compliant' : 'Non-Compliant'}
        </span>
        {algo_id && (
          <span className="compliance-badge__algo-id" title="SEBI Algo ID">
            {algo_id}
          </span>
        )}
      </div>

      {issues.length > 0 && (
        <ul className="compliance-badge__issues">
          {issues.map((issue, i) => (
            <li key={i}>{issue}</li>
          ))}
        </ul>
      )}

      {checked_at && (
        <p className="compliance-badge__ts">
          Checked {new Date(checked_at).toLocaleString()}
        </p>
      )}

      <style>{`
        .compliance-badge {
          border-radius: 10px;
          padding: 10px 14px;
          font-size: 12px;
        }
        .compliance-badge--ok {
          background: rgba(34,197,94,0.08);
          border: 1px solid rgba(34,197,94,0.25);
        }
        .compliance-badge--fail {
          background: rgba(239,68,68,0.08);
          border: 1px solid rgba(239,68,68,0.25);
        }
        .compliance-badge__header {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .compliance-badge__icon {
          font-size: 14px;
          line-height: 1;
        }
        .compliance-badge--ok .compliance-badge__icon   { color: #4ade80; }
        .compliance-badge--fail .compliance-badge__icon { color: #f87171; }
        .compliance-badge__status {
          font-weight: 600;
          font-size: 12px;
        }
        .compliance-badge--ok .compliance-badge__status   { color: #4ade80; }
        .compliance-badge--fail .compliance-badge__status { color: #f87171; }
        .compliance-badge__algo-id {
          margin-left: auto;
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px;
          color: #64748b;
          background: rgba(255,255,255,0.05);
          padding: 2px 7px;
          border-radius: 4px;
        }
        .compliance-badge__issues {
          margin: 8px 0 0;
          padding: 0 0 0 14px;
          list-style: disc;
          color: #fca5a5;
          font-size: 11px;
          line-height: 1.7;
        }
        .compliance-badge__ts {
          margin: 6px 0 0;
          font-size: 10px;
          color: #334155;
        }
      `}</style>
    </div>
  )
}
