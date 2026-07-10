import type { PreviewTransaction } from '../types'

interface TransactionPreviewProps {
  transactions: PreviewTransaction[]
  onApprove: () => void
  onReject: () => void
  isLoading: boolean
}

export function TransactionPreview({
  transactions,
  onApprove,
  onReject,
  isLoading,
}: TransactionPreviewProps) {
  const totalAmount = transactions.reduce((sum, tx) => sum + tx.amount, 0)

  return (
    <div className="preview-modal">
      <div className="preview-content">
        <div className="preview-header">
          <h2>📋 Preview Transactions</h2>
          <p className="preview-subtitle">
            {transactions.length} tranzacții vor fi adăugate. Confirmă sau anulează.
          </p>
        </div>

        <div className="preview-summary">
          <div className="summary-card">
            <span className="summary-label">Transactions</span>
            <span className="summary-value">{transactions.length}</span>
          </div>
          <div className="summary-card">
            <span className="summary-label">Total</span>
            <span className="summary-value" style={{ color: totalAmount < 0 ? '#ef4444' : '#10b981' }}>
              {Math.abs(totalAmount).toFixed(2)} MDL
            </span>
          </div>
        </div>

        <div className="transactions-list">
          {transactions.map((tx, i) => (
            <div key={i} className="tx-item">
              <div className="tx-header">
                <strong>{tx.shop}</strong>
                <span className="tx-amount" style={{ color: tx.amount < 0 ? '#ef4444' : '#10b981' }}>
                  {tx.amount < 0 ? '−' : '+'}{Math.abs(tx.amount).toFixed(2)} {tx.currency}
                </span>
              </div>
              <div className="tx-footer">
                <small className="tx-date">{tx.date}</small>
              </div>
            </div>
          ))}
        </div>

        <div className="preview-actions">
          <button
            className="btn btn-reject"
            onClick={onReject}
            disabled={isLoading}
          >
            ❌ Reject
          </button>
          <button
            className="btn btn-approve"
            onClick={onApprove}
            disabled={isLoading}
          >
            ✅ Approve & Save
          </button>
        </div>
      </div>
    </div>
  )
}
