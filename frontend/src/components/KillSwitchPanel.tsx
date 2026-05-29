import { useState } from 'react'
import { ShieldAlert, ShieldCheck } from 'lucide-react'
import {
  useKillSwitch,
  useResetKillSwitch,
  useTriggerKillSwitch,
} from '../hooks/useTrading'
import { formatDateTime } from '../lib/format'
import { readApiError } from '../lib/api'

interface Props {
  userId: string
}

export function KillSwitchPanel({ userId }: Props) {
  const state = useKillSwitch(userId)
  const trigger = useTriggerKillSwitch(userId)
  const reset = useResetKillSwitch(userId)
  const [reason, setReason] = useState('수동 정지')

  const enabled = state.data?.enabled === true
  const lastErr = trigger.error || reset.error
  const errMsg = lastErr ? readApiError(lastErr) : null

  return (
    <section
      className={`rounded-2xl border shadow-sm p-6 ${
        enabled
          ? 'bg-rose-50 border-rose-300'
          : 'bg-white border-slate-200'
      }`}
    >
      <div className="flex items-start gap-4">
        <div
          className={`p-2 rounded-full ${
            enabled
              ? 'bg-rose-200 text-rose-700'
              : 'bg-emerald-100 text-emerald-700'
          }`}
        >
          {enabled ? (
            <ShieldAlert className="w-5 h-5" />
          ) : (
            <ShieldCheck className="w-5 h-5" />
          )}
        </div>
        <div className="flex-1">
          <h2 className="font-semibold text-slate-900">
            긴급 정지 (Kill Switch)
          </h2>
          <p className="text-sm text-slate-600 mt-1">
            {enabled
              ? '거래가 중단되었습니다. 모든 신규 주문이 거부됩니다.'
              : '거래 정상 — 전략 및 수동 주문이 활성 상태입니다.'}
          </p>

          {enabled && state.data?.reason && (
            <div className="mt-3 text-xs text-rose-700">
              사유: <span className="font-medium">{state.data.reason}</span>
              <span className="text-rose-500 ml-2">
                ({formatDateTime(state.data.triggered_at)})
              </span>
            </div>
          )}

          {!enabled && (
            <div className="mt-4 flex gap-2">
              <input
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="중단 사유"
                className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
              <button
                onClick={() => trigger.mutate({ reason: reason || '수동 정지' })}
                disabled={trigger.isPending}
                className="inline-flex items-center gap-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white px-4 py-1.5 text-sm font-medium disabled:opacity-50"
              >
                <ShieldAlert className="w-4 h-4" />
                정지
              </button>
            </div>
          )}

          {enabled && (
            <button
              onClick={() => reset.mutate()}
              disabled={reset.isPending}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-white border border-rose-300 text-rose-700 hover:bg-rose-100 px-4 py-1.5 text-sm font-medium disabled:opacity-50"
            >
              <ShieldCheck className="w-4 h-4" />
              해제
            </button>
          )}

          {errMsg && (
            <div className="mt-3 text-xs text-rose-700">에러: {errMsg}</div>
          )}
        </div>
      </div>
    </section>
  )
}
