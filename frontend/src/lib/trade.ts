import type { Execution, Trade } from '../api/types'

export const firstEntry = (t: Trade): Execution | undefined => t.executions.find((e) => e.kind === 'entry')
export const firstExit = (t: Trade): Execution | undefined => t.executions.find((e) => e.kind === 'exit')

/** "ES · ESZ2026" for futures, "AAPL" for stocks. */
export function instrumentLabel(t: Trade): string {
  return t.futures_contract ? `${t.instrument.symbol} · ${t.futures_contract.code}` : t.instrument.symbol
}

/** The date a trade is listed under: its entry time, or creation time if still planned. */
export const tradeDate = (t: Trade): string => firstEntry(t)?.executed_at ?? t.created_at
