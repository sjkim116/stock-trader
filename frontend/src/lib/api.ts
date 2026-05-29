/**
 * Typed client for the user-api trading layer.
 *
 * Decimal values come back as strings (the backend serialises with
 * format(d, "f") to preserve precision). The UI parses them with
 * Number() only for display — calculations and comparisons should
 * stay in string form or use a Decimal lib if/when we add one.
 */

import axios from 'axios'

const api = axios.create({
  // Hits the Vite dev proxy in dev (vite.config.ts → /api → :8000)
  // and the same host in prod (ALB serves both).
  baseURL: '/api/v1',
  timeout: 5_000,
})

export interface AccountResponse {
  cash: string
  equity: string
  realized_pnl_today: string
  unrealized_pnl: string
  as_of: string
}

export interface PositionResponse {
  symbol: string
  quantity: string
  avg_entry_price: string
  realized_pnl: string
  notional: string
  opened_at: string
}

export interface PositionsResponse {
  positions: PositionResponse[]
}

export interface OrderResponse {
  order_id: string
  broker_order_id: string | null
  symbol: string
  side: 'buy' | 'sell'
  order_type: string
  quantity: string
  status: string
  price: string | null
  submitted_at: string | null
  error_message: string | null
}

export interface SubmitOrderRequest {
  symbol: string
  side: 'buy' | 'sell'
  quantity: string
  order_type?: 'market' | 'limit'
  user_id?: string
}

export interface KillSwitchState {
  user_id: string
  enabled: boolean
  reason: string | null
  triggered_at: string | null
  updated_at: string
}

export const tradingApi = {
  getAccount: () => api.get<AccountResponse>('/trading/account').then((r) => r.data),

  getPositions: () =>
    api.get<PositionsResponse>('/trading/positions').then((r) => r.data),

  submitOrder: (body: SubmitOrderRequest) =>
    api.post<OrderResponse>('/trading/orders', body).then((r) => r.data),

  getKillSwitch: (userId: string) =>
    api
      .get<KillSwitchState>('/trading/killswitch', { params: { user_id: userId } })
      .then((r) => r.data),

  triggerKillSwitch: (userId: string, reason: string) =>
    api
      .post<KillSwitchState>('/trading/killswitch/trigger', {
        user_id: userId,
        reason,
      })
      .then((r) => r.data),

  resetKillSwitch: (userId: string) =>
    api
      .post<KillSwitchState>('/trading/killswitch/reset', { user_id: userId })
      .then((r) => r.data),
}

/**
 * Normalises an axios error into a string the UI can show. FastAPI
 * returns ``{detail: "..."}`` for 4xx; everything else falls back to
 * the message field.
 */
export function readApiError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail
    if (detail) return detail
    return err.message
  }
  return String(err)
}
