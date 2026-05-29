/**
 * Display helpers — keep formatting out of components.
 *
 * Money is parsed once with Number() purely for display. The raw
 * string from the API is what we'd send back for any computation;
 * we never round it on the way in.
 */

const krw = new Intl.NumberFormat('ko-KR', {
  style: 'currency',
  currency: 'KRW',
  maximumFractionDigits: 0,
})

const number = new Intl.NumberFormat('ko-KR', {
  maximumFractionDigits: 4,
})

export function formatKRW(value: string | number): string {
  const n = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(n)) return value.toString()
  return krw.format(n)
}

export function formatNumber(value: string | number): string {
  const n = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(n)) return value.toString()
  return number.format(n)
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('ko-KR', {
    hour12: false,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function pnlColor(value: string | number): string {
  const n = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(n) || n === 0) return 'text-slate-500'
  return n > 0 ? 'text-rose-600' : 'text-blue-600'
}
