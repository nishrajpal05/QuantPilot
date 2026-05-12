import { useState } from 'react';

export default function AuditBadge({ hash }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!hash) return;
    navigator.clipboard.writeText(hash).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div>
      <div className="card-header">
        <span className="card-title">Audit Hash</span>
        <span className="badge badge-green">SHA-256</span>
      </div>
      <div className="audit-badge">
        <span style={{ color: 'var(--text-muted)', fontSize: 11, whiteSpace: 'nowrap' }}>
          0x
        </span>
        <span className="audit-hash">
          {hash || '—'}
        </span>
        <button
          className={`copy-btn ${copied ? 'copied' : ''}`}
          onClick={handleCopy}
          disabled={!hash}
        >
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      <p style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        color: 'var(--text-dim)',
        marginTop: 8,
        lineHeight: 1.5,
      }}>
        Tamper-proof Merkle hash of symbol · dates · strategy code · results
      </p>
    </div>
  );
}
