import type { DashboardStats, Transaction } from '../types'

interface DashboardProps {
  stats: DashboardStats | null
  recentTransactions: Transaction[]
  isLoading: boolean
}

export function Dashboard({ stats, recentTransactions, isLoading }: DashboardProps) {
  if (isLoading) {
    return (
      <div className="dashboard">
        <div className="skeleton-cards">
          <div className="skeleton"></div>
          <div className="skeleton"></div>
          <div className="skeleton"></div>
        </div>
      </div>
    )
  }

  if (!stats) {
    return <div className="dashboard empty">No data available</div>
  }

  // Get top 3 categories
  const topCategories = Object.entries(stats.byCategory)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3)

  const maxAmount = Math.max(...topCategories.map(([, v]) => v), 1)

  return (
    <div className="dashboard">
      {/* Summary Cards */}
      <div className="stats-cards">
        <div className="stat-card expenses">
          <div className="stat-icon">💸</div>
          <div className="stat-content">
            <span className="stat-label">Total Expenses</span>
            <span className="stat-value">{stats.totalExpenses.toFixed(2)} MDL</span>
          </div>
        </div>

        <div className="stat-card income">
          <div className="stat-icon">💰</div>
          <div className="stat-content">
            <span className="stat-label">Total Income</span>
            <span className="stat-value">{stats.totalIncome.toFixed(2)} MDL</span>
          </div>
        </div>

        <div className="stat-card transactions">
          <div className="stat-icon">📊</div>
          <div className="stat-content">
            <span className="stat-label">Transactions</span>
            <span className="stat-value">{stats.totalTransactions}</span>
          </div>
        </div>
      </div>

      {/* Category Chart */}
      {topCategories.length > 0 && (
        <div className="chart-section">
          <h3>📈 Top Categories</h3>
          <div className="bar-chart">
            {topCategories.map(([category, amount]) => (
              <div key={category} className="bar-item">
                <div className="bar-label">
                  <span className="category-name">{category}</span>
                  <span className="amount">{amount.toFixed(2)} MDL</span>
                </div>
                <div className="bar-container">
                  <div
                    className="bar-fill"
                    style={{
                      width: `${(amount / maxAmount) * 100}%`,
                    }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Transactions */}
      {recentTransactions.length > 0 && (
        <div className="recent-section">
          <h3>🕐 Recent Transactions</h3>
          <div className="transactions-table">
            {recentTransactions.slice(0, 5).map(tx => (
              <div key={tx.id} className="table-row">
                <div className="row-date">{tx.date}</div>
                <div className="row-shop">{tx.shop_name}</div>
                <div className="row-category">{tx.category_name}</div>
                <div className="row-amount" style={{ color: tx.amount < 0 ? '#ef4444' : '#10b981' }}>
                  {tx.amount < 0 ? '−' : '+'}{Math.abs(tx.amount_mdl).toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
