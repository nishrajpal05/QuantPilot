const fmt = {
  pct:    (v) => v != null ? `${(+v).toFixed(2)}%` : '—',
  ratio:  (v) => v != null ? (+v).toFixed(3) : '—',
  int:    (v) => v != null ? Math.round(+v).toLocaleString() : '—',
};

const METRICS = [
  {
    key: 'total_return_pct',
    label: 'Total Return',
    format: fmt.pct,
    accent: (v) => +v >= 0 ? 'var(--green)' : 'var(--red)',
    colorValue: true,
  },
  {
    key: 'cagr',
    label: 'CAGR',
    format: fmt.pct,
    accent: (v) => +v >= 0 ? 'var(--green)' : 'var(--red)',
    colorValue: true,
  },
  {
    key: 'sharpe_ratio',
    label: 'Sharpe Ratio',
    format: fmt.ratio,
    accent: (v) => +v >= 1 ? 'var(--green)' : +v >= 0 ? 'var(--amber)' : 'var(--red)',
    colorValue: true,
  },
  {
    key: 'max_drawdown_pct',
    label: 'Max Drawdown',
    format: (v) => v != null ? `−${Math.abs(+v).toFixed(2)}%` : '—',
    accent: () => 'var(--red)',
    colorValue: false,
    valueColor: 'var(--red)',
  },
  {
    key: 'win_rate',
    label: 'Win Rate',
    format: fmt.pct,
    accent: (v) => +v >= 50 ? 'var(--green)' : 'var(--amber)',
    colorValue: true,
  },
  {
    key: 'total_trades',
    label: 'Total Trades',
    format: fmt.int,
    accent: () => 'var(--blue)',
    colorValue: false,
    valueColor: 'var(--blue)',
  },
];

export default function MetricsGrid({ result }) {
  return (
    <div className="metrics-grid">
      {METRICS.map((m, i) => {
        const raw = result?.[m.key];
        const accentColor = m.accent(raw ?? 0);
        const valueColor = m.colorValue ? accentColor : (m.valueColor || 'var(--text-primary)');

        return (
          <div
            key={m.key}
            className={`metric-card fade-up-${Math.min(i + 1, 5)}`}
            style={{ '--accent-color': accentColor }}
          >
            <div className="metric-label">{m.label}</div>
            <div className="metric-value" style={{ color: valueColor }}>
              {m.format(raw)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
