import { useState } from 'react'
import { Dashboard } from './components/Dashboard'
import { FileUploader } from './components/FileUploader'
import { StatusReport } from './components/StatusReport'
import { TransactionPreview } from './components/TransactionPreview'
import { useDashboard } from './hooks/useDashboard'
import './styles.css'
import type { PreviewTransaction, UploadStatus } from './types'

const API_BASE = ((import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000') as string

type TelegramUser = {
  first_name?: string
  last_name?: string
  username?: string
}

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData?: string
        initDataUnsafe?: {
          user?: TelegramUser
        }
        ready?: () => void
        expand?: () => void
        themeParams?: Record<string, string>
      }
    }
  }
}

function getDisplayName(user?: TelegramUser): string {
  if (!user) {
    return 'Guest'
  }
  return [user.first_name, user.last_name].filter(Boolean).join(' ').trim() || user.username || 'Guest'
}

export default function App() {
  const webApp = window.Telegram?.WebApp
  const displayName = getDisplayName(webApp?.initDataUnsafe?.user)

  webApp?.ready?.()
  webApp?.expand?.()

  // States
  const [status, setStatus] = useState<UploadStatus>('idle')
  const [previewTxs, setPreviewTxs] = useState<PreviewTransaction[]>([])
  const [uploadResult, setUploadResult] = useState<{
    success: boolean
    message: string
    addedCount?: number
    rejectedCount?: number
  } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const { data, stats, loading, error: dashboardError, refetch } = useDashboard()

  // Handle file selection - Upload to backend
  const handleFileSelect = async (file: File) => {
    setError(null)
    setStatus('uploading')
    
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${API_BASE}/api/v1/upload`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Upload failed')
      }

      const data = await response.json()
      
      if (!data.transactions || data.transactions.length === 0) {
        setError('No transactions found in file')
        setStatus('idle')
        return
      }

      setPreviewTxs(data.transactions)
      setStatus('preview')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed'
      setError(message)
      setStatus('idle')
    }
  }

  // Handle approve - Save to backend
  const handleApprove = async () => {
    setStatus('processing')
    setError(null)
    
    try {
      const response = await fetch(`${API_BASE}/api/v1/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transactions: previewTxs }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Save failed')
      }

      const result = await response.json()

      setUploadResult({
        success: result.success !== false,
        message: result.message || 'Transactions saved',
        addedCount: result.added_count || 0,
        rejectedCount: result.rejected_count || 0,
      })
      setStatus('success')
      setPreviewTxs([])
      
      // Refresh dashboard after delay
      setTimeout(() => {
        refetch()
      }, 500)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Save failed'
      setError(message)
      setUploadResult({
        success: false,
        message,
      })
      setStatus('error')
    }
  }

  // Handle reject
  const handleReject = () => {
    setStatus('idle')
    setPreviewTxs([])
    setError(null)
  }

  // Handle dismiss report
  const handleDismissReport = () => {
    setStatus('idle')
    setUploadResult(null)
    setError(null)
  }

  return (
    <main className="app">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <h1 className="app-title">💰 BudgetApp</h1>
          <p className="app-subtitle">Expense Tracker & Analytics</p>
        </div>
        <div className="user-info">
          <span className="user-badge">{displayName}</span>
        </div>
      </header>

      {/* Main Content */}
      <div className="container">
        {/* Upload Section */}
        {(status === 'idle') && (
          <section className="section upload-section">
            <h2 className="section-title">📤 Import Bank Statement</h2>
            <FileUploader
              onFileSelect={handleFileSelect}
              isLoading={false}
            />
            {error && <div className="error-alert">{error}</div>}
          </section>
        )}

        {/* Preview Modal */}
        {(status === 'preview' || status === 'processing') && (
          <TransactionPreview
            transactions={previewTxs}
            onApprove={handleApprove}
            onReject={handleReject}
            isLoading={status === 'processing'}
          />
        )}

        {/* Processing State */}
        {status === 'processing' && (
          <div className="processing-modal">
            <div className="spinner"></div>
            <p>Processing transactions...</p>
          </div>
        )}

        {/* Status Report */}
        {status === 'success' && uploadResult && (
          <StatusReport
            success={uploadResult.success}
            addedCount={uploadResult.addedCount}
            rejectedCount={uploadResult.rejectedCount}
            message={uploadResult.message}
            onDismiss={handleDismissReport}
          />
        )}

        {/* Dashboard */}
        <section className="section dashboard-section">
          <h2 className="section-title">📊 Dashboard</h2>
          <Dashboard
            stats={stats}
            recentTransactions={data?.items || []}
            isLoading={loading}
          />
        </section>
      </div>
    </main>
  )
}