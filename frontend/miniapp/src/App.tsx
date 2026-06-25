import './styles.css'

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

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">Telegram Mini App</p>
        <h1>BudgetApp</h1>
        <p className="lead">
          Unified expense workflows, transaction review, and analytics on the same database as the bot.
        </p>
        <div className="card">
          <span className="label">Signed in as</span>
          <strong>{displayName}</strong>
        </div>
      </section>

      <section className="grid">
        <article className="panel">
          <h2>Import</h2>
          <p>Review bank uploads, parse transactions, and send them to the backend.</p>
        </article>
        <article className="panel">
          <h2>Review</h2>
          <p>Approve, reject, or edit rows before they are stored in PostgreSQL.</p>
        </article>
        <article className="panel">
          <h2>Insights</h2>
          <p>See spending summaries and the same categories used by the Telegram bot.</p>
        </article>
      </section>
    </main>
  )
}