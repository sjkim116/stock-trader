/**
 * React Query hooks wrapping the trading API.
 *
 * Account + positions are polled on a slow interval so the dashboard
 * reflects fills from a strategy tick without forcing the user to
 * refresh. Mutations invalidate the relevant queries on success so
 * the displayed numbers update immediately after an order.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from '@tanstack/react-query'
import {
  tradingApi,
  type AccountResponse,
  type KillSwitchState,
  type OrderResponse,
  type PositionsResponse,
  type SubmitOrderRequest,
} from '../lib/api'

const POLL_MS = 5_000

export const queryKeys = {
  account: ['trading', 'account'] as const,
  positions: ['trading', 'positions'] as const,
  killSwitch: (userId: string) => ['trading', 'killswitch', userId] as const,
}

export function useAccount(): UseQueryResult<AccountResponse> {
  return useQuery({
    queryKey: queryKeys.account,
    queryFn: tradingApi.getAccount,
    refetchInterval: POLL_MS,
  })
}

export function usePositions(): UseQueryResult<PositionsResponse> {
  return useQuery({
    queryKey: queryKeys.positions,
    queryFn: tradingApi.getPositions,
    refetchInterval: POLL_MS,
  })
}

export function useSubmitOrder() {
  const qc = useQueryClient()
  return useMutation<OrderResponse, unknown, SubmitOrderRequest>({
    mutationFn: tradingApi.submitOrder,
    onSuccess: () => {
      // Both account cash and the positions list change after a fill —
      // invalidate both so the next render shows fresh numbers.
      qc.invalidateQueries({ queryKey: queryKeys.account })
      qc.invalidateQueries({ queryKey: queryKeys.positions })
    },
  })
}

export function useKillSwitch(userId: string): UseQueryResult<KillSwitchState> {
  return useQuery({
    queryKey: queryKeys.killSwitch(userId),
    queryFn: () => tradingApi.getKillSwitch(userId),
    refetchInterval: POLL_MS,
    enabled: !!userId,
  })
}

export function useTriggerKillSwitch(userId: string) {
  const qc = useQueryClient()
  return useMutation<KillSwitchState, unknown, { reason: string }>({
    mutationFn: ({ reason }) => tradingApi.triggerKillSwitch(userId, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.killSwitch(userId) })
    },
  })
}

export function useResetKillSwitch(userId: string) {
  const qc = useQueryClient()
  return useMutation<KillSwitchState, unknown, void>({
    mutationFn: () => tradingApi.resetKillSwitch(userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.killSwitch(userId) })
    },
  })
}
