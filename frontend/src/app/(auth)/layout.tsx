import { redirect } from "next/navigation"
import { useAuthLoading } from "@/lib/auth-context"


export default async function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  // Kick off user fetch in the background; the client keeps us mounted.
  // Auth pages are public — render the form immediately. The client-side
  // hook will update UI after tokens are exchanged.
  return (
    <div className="auth-shell">
      <header className="auth-header">
        <div className="auth-logo">
          <span className="auth-logo-mark">CF</span>
          <span className="auth-logo-text">CareerForge</span>
        </div>
        <nav className="auth-nav">
          <a href="/" className="auth-nav-link">Home</a>
          <a href="/pricing" className="auth-nav-link">Pricing</a>
        </nav>
      </header>
      <main className="auth-main">
        <div className="auth-card">{children}</div>
      </main>
      <footer className="auth-footer">
        <p>© {new Date().getFullYear()} CareerForge — AI-powered resume builder.</p>
      </footer>
    </div>
  )
}
