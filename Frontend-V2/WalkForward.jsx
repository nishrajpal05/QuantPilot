import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ReferenceLine,
} from 'recharts'

/**
 * WalkForward
 * @param {{
 *   windows: { window: number, in_sample_sharpe: number, out_sample_sharpe: number }[]
 *   avg_oos_sharpe: number
 *   consistent: boolean
 * }} props
 */
export default function WalkForward({ windows = [], avg_oos_sharpe, consistent }) {
  const data = windows.map(w => ({
    name:   `W${w.window}`,
    'In-Sample':     +w.in_sample_sharpe.toFixed(3),
    'Out-of-Sample': +w.out_sample_sharpe.toFixed(3),
  }))

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    return (
      <div style={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '10px 14px', fontSize: 12 }}>
        <p style={{ color: '#94a3b8', marginBottom: 6 }}>{label}</p>
        {payload.map(p => (
          <p key={p.name} style={{ color: p.fill, margin: '2px 0' }}>
            {p.name}: <strong>{p.value}</strong>
          </p>
        ))}
      </div>
    )
  }

  return (
    <div className="wf-chart">
      <div className="wf-chart__header">
        <span className="wf-chart__title">Walk-Forward Optimization</span>
        <div className="wf-chart__badge" data-consistent={consistent}>
          {consistent ? '✓ Consistent' : '⚠ Inconsistent'}
          <span className="wf-chart__oos">Avg OOS Sharpe: {avg_oos_sharpe?.toFixed(3)}</span>
        </div>
      </div>

      {data.length > 0 ? (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }} barGap={4}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: '#475569' }} width={40} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: 10, paddingTop: 8 }}
              formatter={(v) => <span style={{ color: '#94a3b8' }}>{v}</span>}
            />
            <ReferenceLine y={0.5} stroke="rgba(250,204,21,0.3)" strokeDasharray="4 4" label={{ value: 'target', position: 'right', fontSize: 9, fill: '#ca8a04' }} />
            <ReferenceLine y={0}   stroke="rgba(255,255,255,0.1)" />
            <Bar dataKey="In-Sample"     fill="#3b82f6" radius={[3, 3, 0, 0]} />
            <Bar dataKey="Out-of-Sample" fill="#22c55e" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <div className="wf-chart__empty">No walk-forward data available</div>
      )}

      <p className="wf-chart__note">
        Dashed line = Sharpe 0.5 target. Green bars above line indicate robust OOS performance.
      </p>

      <style>{`
        .wf-chart { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.07); border-radius: 12px; padding: 16px; }
        .wf-chart__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 8px; }
        .wf-chart__title { font-size: 13px; font-weight: 600; color: #e2e8f0; }
        .wf-chart__badge { display: flex; align-items: center; gap: 10px; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 20px; }
        .wf-chart__badge[data-consistent="true"]  { background: rgba(34,197,94,0.12); color: #4ade80; border: 1px solid rgba(34,197,94,0.25); }
        .wf-chart__badge[data-consistent="false"] { background: rgba(251,191,36,0.1); color: #fbbf24; border: 1px solid rgba(251,191,36,0.2); }
        .wf-chart__oos { font-size: 10px; opacity: 0.75; font-weight: 400; }
        .wf-chart__empty { height: 220px; display: flex; align-items: center; justify-content: center; color: #475569; font-size: 13px; }
        .wf-chart__note { margin: 8px 0 0; font-size: 10px; color: #334155; font-style: italic; }
      `}</style>
    </div>
  )
}
