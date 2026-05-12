import { useState } from 'react';

const PAGE_SIZE = 15;
const fmtDate = (d) => d?.slice(0, 10) || '—';
const fmtPnl = (v) => {
  const n = parseFloat(v);
  if (isNaN(n)) return '—';
  const sign = n >= 0 ? '+' : '';
  return `${sign}₹${Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
};

export default function TradeTable({ trades = [] }) {
  const [page, setPage] = useState(1);
  const totalPages = Math.max(1, Math.ceil(trades.length / PAGE_SIZE));
  const slice = trades.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  if (!trades.length) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📋</div>
        <div className="empty-state-title">No trades recorded</div>
        <div className="empty-state-sub">Trade log will appear after backtest completes</div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ overflowX: 'auto' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Entry Date</th>
              <th>Exit Date</th>
              <th>P&amp;L</th>
              <th>Return %</th>
            </tr>
          </thead>
          <tbody>
            {slice.map((trade, i) => {
              const pnl = parseFloat(trade.pnl);
              const isPos = pnl >= 0;
              const idx = (page - 1) * PAGE_SIZE + i + 1;
              return (
                <tr key={i}>
                  <td style={{ color: 'var(--text-dim)' }}>{idx}</td>
                  <td>{fmtDate(trade.entry_date)}</td>
                  <td>{fmtDate(trade.exit_date)}</td>
                  <td className={isPos ? 'td-positive' : 'td-negative'}>{fmtPnl(pnl)}</td>
                  <td className={isPos ? 'td-positive' : 'td-negative'}>
                    {trade.return_pct != null
                      ? `${isPos ? '+' : ''}${parseFloat(trade.return_pct).toFixed(2)}%`
                      : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button
            className="page-btn"
            onClick={() => setPage(1)}
            disabled={page === 1}
          >«</button>
          <button
            className="page-btn"
            onClick={() => setPage((p) => p - 1)}
            disabled={page === 1}
          >‹</button>

          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            let p;
            if (totalPages <= 5) p = i + 1;
            else if (page <= 3) p = i + 1;
            else if (page >= totalPages - 2) p = totalPages - 4 + i;
            else p = page - 2 + i;
            return (
              <button
                key={p}
                className={`page-btn ${page === p ? 'active' : ''}`}
                onClick={() => setPage(p)}
              >{p}</button>
            );
          })}

          <button
            className="page-btn"
            onClick={() => setPage((p) => p + 1)}
            disabled={page === totalPages}
          >›</button>
          <button
            className="page-btn"
            onClick={() => setPage(totalPages)}
            disabled={page === totalPages}
          >»</button>

          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)', marginLeft: 8 }}>
            {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, trades.length)} of {trades.length}
          </span>
        </div>
      )}
    </div>
  );
}
