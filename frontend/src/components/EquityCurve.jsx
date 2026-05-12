import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';

const fmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const val = payload[0].value;
  const start = payload[0].payload._start;
  const pct = start ? (((val - start) / start) * 100).toFixed(2) : null;

  return (
    <div style={{
      background: 'var(--bg-elevated)',
      border: '1px solid var(--border-bright)',
      borderRadius: 'var(--radius-sm)',
      padding: '10px 14px',
      fontFamily: 'var(--font-mono)',
      fontSize: 12,
    }}>
      <div style={{ color: 'var(--text-muted)', fontSize: 10, marginBottom: 4 }}>{label}</div>
      <div style={{ color: 'var(--green)', fontWeight: 700, fontSize: 15 }}>{fmt.format(val)}</div>
      {pct !== null && (
        <div style={{ color: +pct >= 0 ? 'var(--green)' : 'var(--red)', fontSize: 11, marginTop: 2 }}>
          {+pct >= 0 ? '+' : ''}{pct}% from start
        </div>
      )}
    </div>
  );
}

export default function EquityCurve({ data = [] }) {
  if (!data.length) {
    return (
      <div className="empty-state" style={{ minHeight: 200 }}>
        <div className="empty-state-icon">📈</div>
        <div className="empty-state-title">No equity data</div>
      </div>
    );
  }

  const startVal = data[0]?.value;
  const endVal = data[data.length - 1]?.value;
  const isPositive = endVal >= startVal;

  const enriched = data.map((d) => ({ ...d, _start: startVal }));

  const minVal = Math.min(...data.map((d) => d.value));
  const maxVal = Math.max(...data.map((d) => d.value));
  const pad = (maxVal - minVal) * 0.08;

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={enriched} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
        <defs>
          <linearGradient id="eq-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor={isPositive ? '#00d464' : '#ff4757'} stopOpacity={0.25} />
            <stop offset="95%" stopColor={isPositive ? '#00d464' : '#ff4757'} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fill: 'var(--text-dim)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
          tickFormatter={(v) => v?.slice(0, 7)}
        />
        <YAxis
          tick={{ fill: 'var(--text-dim)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
          tickLine={false}
          axisLine={false}
          domain={[minVal - pad, maxVal + pad]}
          tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
          width={52}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'var(--border-bright)', strokeWidth: 1 }} />
        <Area
          type="monotone"
          dataKey="value"
          stroke={isPositive ? '#00d464' : '#ff4757'}
          strokeWidth={2}
          fill="url(#eq-grad)"
          dot={false}
          activeDot={{ r: 4, fill: isPositive ? '#00d464' : '#ff4757', strokeWidth: 0 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
