import { useEffect, useState } from 'react'
import type { DashboardStats, TransactionSummary } from '../types'

const API_BASE = ((import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000') as string

export function useDashboard() {
  const [data, setData] = useState<TransactionSummary | null>(null)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchDashboard = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/api/v1/transactions?limit=50`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const json: TransactionSummary = await response.json()
      setData(json)

      // Calculate category stats
      const byCategory: Record<string, number> = {}
      json.items.forEach(tx => {
        const cat = tx.category_name || 'Uncategorized'
        byCategory[cat] = (byCategory[cat] || 0) + Math.abs(tx.amount_mdl)
      })

      setStats({
        totalExpenses: json.summary.total_expenses,
        totalIncome: json.summary.total_income,
        totalTransactions: json.summary.total_transactions,
        byCategory,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboard()
    // Refresh every 30 seconds
    const interval = setInterval(fetchDashboard, 30000)
    return () => clearInterval(interval)
  }, [])

  return { data, stats, loading, error, refetch: fetchDashboard }
}
