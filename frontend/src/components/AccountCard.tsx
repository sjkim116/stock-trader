import { Wallet, TrendingUp, TrendingDown, Activity } from 'lucide-react'
import { useAccount } from '../hooks/useTrading'
import { formatKRW, formatDateTime, pnlColor } from '../lib/format'

export function AccountCard() {
  const { data, isLoading, isError, error } = useAccount()

  if (isLoading) {
    return (
      <section className="rounded-2xl bg-white shadow-sm border border-slate-200 p-6 animate-pulse">
        <div className="h-5 w-24 bg-slate-200 rounded mb-4" />
        <div className="h-10 w-48 bg-slate-200 rounded mb-2" />
        <div className="h-4 w-32 bg-slate-200 rounded" />
      </section>
    )
  }

  if (isError || !data) {
    return (
      <section className="rounded-2xl bg-rose-50 border border-rose-200 p-6 text-rose-700">
        <div className="font-semibold mb-1">계좌 정보를 불러오지 못함</div>
        <div className="text-sm">{String(error)}</div>
      </section>
    )
  }

  const realized = Number(data.realized_pnl_today)
  const unrealized = Number(data.unrealized_pnl)

  return (
    <section className="rounded-2xl bg-white shadow-sm border border-slate-200 p-6">
      <div className="flex items-center gap-2 text-slate-500 text-sm mb-4">
        <Wallet className="w-4 h-4" />
        <span>계좌 현황</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Metric
          label="현금"
          value={formatKRW(data.cash)}
          icon={<Wallet className="w-5 h-5 text-slate-400" />}
        />
        <Metric
          label="총 평가금액"
          value={formatKRW(data.equity)}
          icon={<Activity className="w-5 h-5 text-slate-400" />}
        />
        <Metric
          label="오늘 실현/평가 손익"
          value={
            <span>
              <span className={pnlColor(realized)}>{formatKRW(realized)}</span>
              <span className="text-slate-400 mx-1">/</span>
              <span className={pnlColor(unrealized)}>{formatKRW(unrealized)}</span>
            </span>
          }
          icon={
            realized + unrealized >= 0 ? (
              <TrendingUp className="w-5 h-5 text-rose-400" />
            ) : (
              <TrendingDown className="w-5 h-5 text-blue-400" />
            )
          }
        />
      </div>
      <div className="text-xs text-slate-400 mt-4">
        최근 갱신 {formatDateTime(data.as_of)}
      </div>
    </section>
  )
}

function Metric({
  label,
  value,
  icon,
}: {
  label: string
  value: React.ReactNode
  icon: React.ReactNode
}) {
  return (
    <div>
      <div className="flex items-center gap-2 text-slate-500 text-xs mb-1">
        {icon}
        <span>{label}</span>
      </div>
      <div className="text-2xl font-semibold text-slate-900">{value}</div>
    </div>
  )
}
