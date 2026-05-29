import { useState } from 'react'
import { Send } from 'lucide-react'
import { useSubmitOrder } from '../hooks/useTrading'
import { readApiError } from '../lib/api'

export function OrderForm() {
  const [symbol, setSymbol] = useState('005930')
  const [side, setSide] = useState<'buy' | 'sell'>('buy')
  const [quantity, setQuantity] = useState('10')
  const submit = useSubmitOrder()

  const last = submit.data
  const errMsg = submit.error ? readApiError(submit.error) : null

  return (
    <section className="rounded-2xl bg-white shadow-sm border border-slate-200 p-6">
      <h2 className="font-semibold text-slate-900 mb-4">주문</h2>
      <form
        className="grid grid-cols-1 md:grid-cols-12 gap-3"
        onSubmit={(e) => {
          e.preventDefault()
          if (!symbol || !quantity) return
          submit.mutate({ symbol, side, quantity })
        }}
      >
        <label className="md:col-span-4">
          <span className="block text-xs text-slate-500 mb-1">종목코드</span>
          <input
            type="text"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.trim())}
            placeholder="005930"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </label>
        <label className="md:col-span-3">
          <span className="block text-xs text-slate-500 mb-1">매수/매도</span>
          <select
            value={side}
            onChange={(e) => setSide(e.target.value as 'buy' | 'sell')}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="buy">매수</option>
            <option value="sell">매도</option>
          </select>
        </label>
        <label className="md:col-span-3">
          <span className="block text-xs text-slate-500 mb-1">수량</span>
          <input
            type="number"
            min={1}
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </label>
        <button
          type="submit"
          disabled={submit.isPending}
          className={`md:col-span-2 inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 font-medium text-white transition ${
            side === 'buy'
              ? 'bg-rose-600 hover:bg-rose-700'
              : 'bg-blue-600 hover:bg-blue-700'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          <Send className="w-4 h-4" />
          {submit.isPending ? '제출 중…' : '제출'}
        </button>
      </form>

      {last && !errMsg && (
        <div className="mt-4 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 text-sm">
          <span className="font-medium">{last.symbol}</span>{' '}
          {last.side === 'buy' ? '매수' : '매도'} {last.quantity}주{' '}
          체결됨{' '}
          <span className="text-emerald-600">
            (주문번호 {last.broker_order_id ?? last.order_id.slice(0, 8)})
          </span>
        </div>
      )}
      {errMsg && (
        <div className="mt-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 px-4 py-3 text-sm">
          주문 거부됨: {errMsg}
        </div>
      )}
    </section>
  )
}
