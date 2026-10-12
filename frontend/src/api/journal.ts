import { apiDelete, apiGet, apiPatch, apiPost, apiPut, toQuery } from './client'
import type {
  AccountType,
  AssetClass,
  FuturesContract,
  Instrument,
  Portfolio,
  Strategy,
  Trade,
  TradeFilters,
  TradeInput,
} from './types'

// ---- portfolios & strategies ----
export const listPortfolios = () => apiGet<Portfolio[]>('/portfolios')
export const createPortfolio = (body: { name: string; account_type: AccountType; starting_capital: string; description?: string | null }) =>
  apiPost<Portfolio>('/portfolios', body)
export const updatePortfolio = (id: number, body: Partial<Pick<Portfolio, 'name' | 'account_type' | 'starting_capital' | 'description'>>) =>
  apiPatch<Portfolio>(`/portfolios/${id}`, body)
export const deletePortfolio = (id: number) => apiDelete(`/portfolios/${id}`)

export const listStrategies = () => apiGet<Strategy[]>('/strategies')
export const createStrategy = (body: { name: string; description?: string | null }) => apiPost<Strategy>('/strategies', body)

// ---- instruments ----
export const listInstruments = (asset_class?: AssetClass, q?: string) =>
  apiGet<Instrument[]>(`/instruments${toQuery({ asset_class, q })}`)
export const createStock = (body: { symbol: string; name: string }) => apiPost<Instrument>('/instruments/stocks', body)
export const listContracts = (instrumentId: number) => apiGet<FuturesContract[]>(`/instruments/${instrumentId}/contracts`)
export const createContract = (instrumentId: number, body: { contract_month: string; expiration_date: string }) =>
  apiPost<FuturesContract>(`/instruments/${instrumentId}/contracts`, body)

// ---- trades ----
export const listTrades = (filters: TradeFilters) => apiGet<Trade[]>(`/trades${toQuery({ ...filters })}`)
export const getTrade = (id: number) => apiGet<Trade>(`/trades/${id}`)
export const createTrade = (body: TradeInput) => apiPost<Trade>('/trades', body)
export const replaceTrade = (id: number, body: TradeInput) => apiPut<Trade>(`/trades/${id}`, body)
export const deleteTrade = (id: number) => apiDelete(`/trades/${id}`)
