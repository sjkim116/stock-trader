import { Briefcase } from 'lucide-react'
import { usePositions } from '../hooks/useTrading'
import { formatKRW, formatNumber, pnlColor } from '../lib/format'

export function PositionsTable() {
  const { data, isLoading, isError, error } = usePositions()

  return (
    <section className="rounded-2xl bg-white shadow-sm border border-slate-200">
      <header className="flex items-center gap-2 px-6 py-4 border-b border-slate-100">
        <Briefcase className="w-4 h-4 text-slate-500" />
        <h2 className="font-semibold text-slate-900">보유 포지션</h2>
        <span className="text-sm text-slate-400">
          ({data?.positions.length ?? 0})
        </span>
      </header>

      {isLoading && (
        <div className="px-6 py-8 text-slate-400 text-sm">로딩 중…</div>
      )}
      {isError && (
        <div className="px-6 py-8 text-rose-600 text-sm">
          포지션을 불러오지 못함: {String(error)}
        </div>
      )}
      {!isLoading && !isError && data && data.positions.length === 0 && (
        <div className="px-6 py-12 text-center text-slate-400 text-sm">
          현재 보유 중인 포지션이 없습니다.
        </div>
      )}

      {data && data.positions.length > 0 && (
        <table className="w-full text-sm">
          <thead className="text-xs text-slate-500 bg-slate-50">
            <tr>
              <th className="text-left px-6 py-2 font-medium">종목</th>
              <th className="text-right px-6 py-2 font-medium">수량</th>
              <th className="text-right px-6 py-2 font-medium">평균단가</th>
              <th className="text-right px-6 py-2 font-medium">평가금액</th>
              <th className="text-right px-6 py-2 font-medium">실현 손익</th>
            </tr>
          </thead>
          <tbody>
            {data.positions.map((p) => (
              <tr key={p.symbol} className="border-t border-slate-100">
                <td className="px-6 py-3 font-mono text-slate-900">{p.symbol}</td>
                <td className="px-6 py-3 text-right text-slate-700">
                  {formatNumber(p.quantity)}
                </td>
                <td className="px-6 py-3 text-right text-slate-700">
                  {formatKRW(p.avg_entry_price)}
                </td>
                <td className="px-6 py-3 text-right text-slate-700">
                  {formatKRW(p.notional)}
                </td>
                <td
                  className={`px-6 py-3 text-right font-medium ${pnlColor(
                    p.realized_pnl
                  )}`}
                >
                  {formatKRW(p.realized_pnl)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
