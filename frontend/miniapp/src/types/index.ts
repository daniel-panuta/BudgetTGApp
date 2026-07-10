// API Response Types
export interface Transaction {
  id: number
  date: string
  amount: number
  currency: string
  amount_original: number
  amount_mdl: number
  raw_text: string
  shop_name: string
  category_name: string
}

export interface TransactionSummary {
  items: Transaction[]
  summary: {
    total_transactions: number
    total_expenses: number
    total_income: number
  }
}

// Frontend State Types
export interface PreviewTransaction {
  shop: string
  amount: number
  currency: string
  date: string
  raw_text: string
}

export interface UploadResponse {
  success: boolean
  message: string
  added_count?: number
  rejected_count?: number
}

export interface DashboardStats {
  totalExpenses: number
  totalIncome: number
  totalTransactions: number
  byCategory: Record<string, number>
}

export type UploadStatus = 'idle' | 'uploading' | 'preview' | 'processing' | 'success' | 'error'
