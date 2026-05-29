import { AccountCard } from './components/AccountCard'
import { KillSwitchPanel } from './components/KillSwitchPanel'
import { OrderForm } from './components/OrderForm'
import { PositionsTable } from './components/PositionsTable'

// Hardcoded user UUID for the personal-use tool. When Cognito wiring
// lands this comes from the auth context.
const DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000001'

function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-slate-900">
              AlgoTrader Pro
            </h1>
            <p className="text-xs text-slate-500">
              개인용 단타 매매 대시보드 · 모의투자
            </p>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            user: {DEFAULT_USER_ID.slice(0, 8)}…
          </span>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <AccountCard />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <OrderForm />
            <PositionsTable />
          </div>
          <div>
            <KillSwitchPanel userId={DEFAULT_USER_ID} />
          </div>
        </div>
      </main>

      <footer className="max-w-6xl mx-auto px-6 py-8 text-center text-xs text-slate-400">
        본인 자산 운용 도구 · 거래 결과의 책임은 사용자에게 있습니다
      </footer>
    </div>
  )
}

export default App
