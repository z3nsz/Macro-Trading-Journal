import { describe, expect, it } from 'vitest'
import { formatMoney, formatPrice, formatR, pnlColor, isoToLocalInput, localInputToIso, toThirtySeconds, trimDecimal } from './format'

describe('trimDecimal', () => {
  it('removes trailing zeros without float rounding', () => {
    expect(trimDecimal('5000.2500000000')).toBe('5000.25')
    expect(trimDecimal('2.000000')).toBe('2')
    expect(trimDecimal('0.0000500000')).toBe('0.00005')
    expect(trimDecimal('123456789012.1234567891')).toBe('123456789012.1234567891')
  })
  it('shows a dash for missing values', () => {
    expect(trimDecimal(null)).toBe('—')
  })
})

describe('Treasury 32nds', () => {
  it('formats ZB in whole 32nds', () => {
    expect(toThirtySeconds('112.53125', 'thirty_seconds')).toBe("112'17")
    expect(toThirtySeconds('112.0000000000', 'thirty_seconds')).toBe("112'00")
  })
  it('formats ZN in half 32nds', () => {
    expect(toThirtySeconds('112.515625', 'half_thirty_seconds')).toBe("112'16.5")
    expect(toThirtySeconds('110.984375', 'half_thirty_seconds')).toBe("110'31.5")
  })
  it('refuses prices that are not on the 32nds grid', () => {
    expect(toThirtySeconds('112.51', 'half_thirty_seconds')).toBeNull()
    expect(toThirtySeconds('112.515625', 'thirty_seconds')).toBeNull() // half-32nd is not a ZB tick
  })
  it('falls back to the decimal when not representable', () => {
    expect(formatPrice('112.51', 'half_thirty_seconds')).toBe('112.51')
    expect(formatPrice('5000.25', 'decimal')).toBe('5000.25')
  })
})

describe('local time <-> UTC', () => {
  it('round-trips a datetime-local value', () => {
    const iso = localInputToIso('2026-10-01T09:30')
    expect(iso.endsWith('Z')).toBe(true)
    expect(isoToLocalInput(iso)).toBe('2026-10-01T09:30')
  })
})

describe('formatMoney', () => {
  it('always shows cents and thousands separators', () => {
    expect(formatMoney('4.2')).toBe('$4.20')
    expect(formatMoney('4.20')).toBe('$4.20')
    expect(formatMoney('100000.00')).toBe('$100,000.00')
    expect(formatMoney('-1234.5')).toBe('-$1,234.50')
    expect(formatMoney('0')).toBe('$0.00')
  })
})

describe('formatR and pnlColor', () => {
  it('labels R multiples', () => {
    expect(formatR('1.98')).toBe('1.98R')
    expect(formatR(null)).toBe('—')
  })
  it('colors gains, losses and zero', () => {
    expect(pnlColor('4016.60')).toBe('text-emerald-700')
    expect(pnlColor('-2000.00')).toBe('text-red-700')
    expect(pnlColor('0.00')).toBe('text-slate-500')
    expect(pnlColor(null)).toBe('text-slate-500')
  })
})
