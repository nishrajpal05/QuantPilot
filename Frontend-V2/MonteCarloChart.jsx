import { useMemo } from 'react'
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine,
} from 'recharts'

/**
 * MonteCarloChart
 * @param {{
 *   simulations: number[][]  - array of 100 paths, each path = array of daily multipliers
 *   percentile_5: number
 *   percentile_95: number
 *   median_return: number
 *   prob_profit: number
 * }} props
 */
export default function MonteCarloChart({ simulations = [], percentile_5, percentile_95, median_return, prob_profit }) {
  // Build chart data: for each day, collect p5, p25, p50, p75, p95
  const data = useMemo(() => {
    if (!simulations?.length) return []
    const numDays = simulations[0]?.length ?? 252

    return Array.from({ length: numDays }, (_, day) => {
      const vals = simulations
        .map(path => path[day])
        .sort((a, b) => a - b)

      const pct = (p) => vals[Math.floor((p / 100) * vals.length)] ?? 1

      return {
        day,
        p5:  pct(5)  * 100 - 100,
        p25: pct(25) * 100 - 100,
        p50: pct(50) * 100 - 100,
        p75: pct(75) * 100 - 100,
        p95: pct(95) * 100 - 100,
      }
    })
  }, [simulations])

  const fmt = (v) => `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`

  return (
    <div className="mc-chart">
      <div className="mc-chart__header">
        <span className="mc-chart__title">Monte Carlo Simulation</span>
        <div className="mc-chart__stats">
          <Stat label="Median" value={fmt((median_return - 1) * 100)} color="#a78bfa" />
          <Stat label="5th pct" value={fmt((percentile_5 - 1) * 100)} color="#f87171" />
          <Stat label="95th pct" value={fmt((percentile_95 - 1) * 100)} color="#34d399" />
          <Stat label="P(profit)" value={`${(prob_profit * 100).toFixed(0)}%`} color="#60a5fa" />
        </div>
      </div>

      {data.length > 0 ? (
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="mc-outer" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#7c3aed" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#7c3aed" stopOpacity={0.05} />
              </linearGradient>
              <linearGradient id="mc-inner" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#8b5cf6" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="day"
              tick={{ fontSize: 10, fill: '#475569' }}
              tickFormatter={(v) => `D${v}`}
              interval={Math.floor(data.length / 6)}
            />
            <YAxis
              tick={{ fontSize: 10, fill: '#475569' }}
              tickFormatter={fmt}
              width={52}
            />
            <Tooltip
              contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }}
              labelFormatter={(v) => `Day ${v}`}
              formatter={(v, name) => [fmt(v), name]}
            />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.2)" strokeDasharray="4 4" />
            {/* Outer band: p5–p95 */}
            <Area type="monotone" dataKey="p95" stroke="none" fill="url(#mc-outer)" fillOpacity={1} />
            <Area type="monotone" dataKey="p5"  stroke="none" fill="#0f172a"        fillOpacity={1} />
            {/* Inner band: p25–p75 */}
            <Area type="monotone" dataKey="p75" stroke="none" fill="url(#mc-inner)" fillOpacity={1} />
            <Area type="monotone" dataKey="p25" stroke="none" fill="#0f172a"        fillOpacity={1} />
            {/* Median line */}
            <Area type="monotone" dataKey="p50" stroke="#a78bfa" strokeWidth={2} fill="none" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div className="mc-chart__empty">No simulation data available</div>
      )}

      <div className="mc-chart__legend">
        <LegendItem color="rgba(124,58,237,0.3)" label="P5–P95 range" />
        <LegendItem color="rgba(139,92,246,0.5)" label="P25–P75 range" />
        <LegendItem color="#a78bfa" label="Median path" solid />
      </div>

      <style>{`
        .mc-chart { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.07); border-radius: 12px; padding: 16px; }
        .mc-chart__header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; flex-wrap: wrap; gap: 10px; }
        .mc-chart__title { font-size: 13px; font-weight: 600; color: #e2e8f0; letter-spacing: 0.02em; }
        .mc-chart__stats { display: flex; gap: 16px; flex-wrap: wrap; }
        .mc-stat { display: flex; flex-direction: column; align-items: flex-end; }
        .mc-stat__label { font-size: 9px; text-transform: uppercase; letter-spacing: 0.08em; color: #475569; }
        .mc-stat__value { font-size: 13px; font-weight: 600; font-family: 'JetBrains Mono', monospace; }
        .mc-chart__empty { height: 260px; display: flex; align-items: center; justify-content: center; color: #475569; font-size: 13px; }
        .mc-chart__legend { display: flex; gap: 16px; margin-top: 10px; flex-wrap: wrap; }
        .mc-legend-item { display: flex; align-items: center; gap: 6px; font-size: 10px; color: #64748b; }
        .mc-legend-swatch { width: 20px; height: 8px; border-radius: 2px; }
        .mc-legend-swatch--solid { height: 2px; border-radius: 1px; }
      `}</style>
    </div>
  )
}

function Stat({ label, value, color }) {
  return (
    <div className="mc-stat">
      <span className="mc-stat__label">{label}</span>
      <span className="mc-stat__value" style={{ color }}>{value}</span>
    </div>
  )
}

function LegendItem({ color, label, solid }) {
  return (
    <div className="mc-legend-item">
      <div
        className={`mc-legend-swatch ${solid ? 'mc-legend-swatch--solid' : ''}`}
        style={{ background: color }}
      />
      {label}
    </div>
  )
}
