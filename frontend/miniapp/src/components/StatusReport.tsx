interface StatusReportProps {
  success: boolean
  addedCount?: number
  rejectedCount?: number
  message: string
  onDismiss: () => void
}

export function StatusReport({
  success,
  addedCount = 0,
  rejectedCount = 0,
  message,
  onDismiss,
}: StatusReportProps) {
  return (
    <div className={`status-report ${success ? 'success' : 'error'}`}>
      <div className="status-icon">
        {success ? '✅' : '⚠️'}
      </div>
      <div className="status-content">
        <h3 className="status-title">
          {success ? 'Upload Successful!' : 'Upload Failed'}
        </h3>
        <p className="status-message">{message}</p>

        {success && (
          <div className="status-stats">
            <div className="stat">
              <span className="stat-num">{addedCount}</span>
              <span className="stat-label">tranzacții adăugate</span>
            </div>
            {rejectedCount > 0 && (
              <div className="stat error">
                <span className="stat-num">{rejectedCount}</span>
                <span className="stat-label">respinse (duplicate)</span>
              </div>
            )}
          </div>
        )}
      </div>
      <button className="btn btn-dismiss" onClick={onDismiss}>
        OK
      </button>
    </div>
  )
}
