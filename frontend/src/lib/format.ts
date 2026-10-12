// Display helpers. Values from the API are decimal strings; we format them without
// converting to floating point where precision matters.

import type { PriceFormat } from '../api/types'

/** "5000.2500000000" -> "5000.25", "2.000000" -> "2". Pure string work, no float rounding. */
export function trimDecimal(value: string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  if (!value.includes('.')) return value
  const trimmed = value.replace(/0+$/, '').replace(/\.$/, '')
  return trimmed === '-0' ? '0' : trimmed
}

/** Money with exactly 2 decimals and thousands separators: "1234.5" -> "$1,234.50". String-based. */
export function formatMoney(value: string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  const negative = value.startsWith('-')
  const [whole, frac = ''] = value.replace('-', '').split('.')
  // Values from the API already have at most 2 decimals for money; pad to exactly 2.
  const cents = (frac + '00').slice(0, 2)
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return `${negative ? '-' : ''}$${grouped}.${cents}`
}

/**
 * Treasury futures are quoted in points and 32nds:
 *   ZB  thirty_seconds:       112.53125  -> "112'17"     (17/32)
 *   ZN  half_thirty_seconds:  112.515625 -> "112'16.5"   (16½/32)
 * Returns null if the value can't be written that way (e.g. off-tick input).
 */
export function toThirtySeconds(value: string, format: PriceFormat): string | null {
  if (format === 'decimal') return null
  const n = Number(value)
  if (!Number.isFinite(n) || n <= 0) return null
  const whole = Math.floor(n)
  // 1/64 fractions are exact in binary floating point, so this arithmetic is exact for valid ticks.
  const thirtySeconds = (n - whole) * 32
  const step = format === 'thirty_seconds' ? 1 : 0.5
  if (Math.abs(thirtySeconds / step - Math.round(thirtySeconds / step)) > 1e-9) return null
  const whole32 = Math.floor(thirtySeconds)
  const half = thirtySeconds - whole32 >= 0.5
  return `${whole}'${String(whole32).padStart(2, '0')}${half ? '.5' : ''}`
}

/** Price for display: decimal for most contracts, 32nds notation for Treasuries. */
export function formatPrice(value: string | null | undefined, format: PriceFormat = 'decimal'): string {
  if (value === null || value === undefined || value === '') return '—'
  return toThirtySeconds(value, format) ?? trimDecimal(value)
}

/** "2026-10-01T14:30:00Z" -> "Oct 1, 2026, 9:30 AM" in the viewer's local timezone. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

/** Value for <input type="datetime-local"> (local time, no timezone) from an ISO string. */
export function isoToLocalInput(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** "2026-10-01T09:30" typed in local time -> "2026-10-01T14:30:00.000Z" (UTC) for the API. */
export function localInputToIso(local: string): string {
  return new Date(local).toISOString()
}

export const STATUS_LABELS: Record<string, string> = {
  planned: 'Planned',
  open: 'Open',
  partially_closed: 'Partially closed',
  closed: 'Closed',
}
