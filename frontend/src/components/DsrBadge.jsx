export default function DsrBadge({ score }) {
  const num = parseFloat(score);
  const isPass = num >= 0.5;
  const isWarn = num >= 0.3 && num < 0.5;
  const cls = isPass ? 'dsr-pass' : isWarn ? 'dsr-warn' : 'dsr-fail';

  const label = isPass ? 'Not Overfit' : isWarn ? 'Borderline' : 'Likely Overfit';
  const desc = isPass
    ? 'Strategy shows genuine edge on out-of-sample data'
    : isWarn
    ? 'Marginal — validate with additional data'
    : 'High risk of curve-fitting; results may not hold live';

  return (
    <div className={`dsr-badge ${cls}`}>
      <div>
        <div className="dsr-score-num">{isNaN(num) ? '—' : num.toFixed(2)}</div>
      </div>
      <div>
        <div className="dsr-label">DSR · {label}</div>
        <div className="dsr-desc">{desc}</div>
      </div>
    </div>
  );
}
