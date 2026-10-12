// TypeScript mirrors of the backend's Pydantic schemas (backend/app/schemas/).
// Decimal values arrive as strings, e.g. "5000.2500000000", to keep exact precision.

export type Decimal = string
export type AccountType = 'simulated' | 'real'
export type AssetClass = 'stock' | 'future'
export type Direction = 'long' | 'short'
export type TradeStatus = 'planned' | 'open' | 'partially_closed' | 'closed'
export type PriceFormat = 'decimal' | 'thirty_seconds' | 'half_thirty_seconds'

export interface Portfolio {
  id: number
  name: string
  account_type: AccountType
  starting_capital: Decimal
  currency: string
  description: string | null
  created_at: string
}

export interface Strategy {
  id: number
  name: string
  description: string | null
}

export interface Instrument {
  id: number
  asset_class: AssetClass
  symbol: string
  name: string
  exchange: string | null
  currency: string
  price_unit: string
  price_format: PriceFormat
  tick_size: Decimal | null
  point_value: Decimal
  tick_value: Decimal | null
  spec_source_url: string | null
  spec_verified_on: string | null
}

export interface FuturesContract {
  id: number
  instrument_id: number
  code: string
  contract_month: string
  expiration_date: string
}

export interface Execution {
  id: number
  kind: 'entry' | 'exit'
  quantity: Decimal
  price: Decimal
  executed_at: string
  fees: Decimal
}

export interface Trade {
  id: number
  portfolio: { id: number; name: string; account_type: AccountType }
  instrument: Instrument
  futures_contract: FuturesContract | null
  strategy: Strategy | null
  direction: Direction
  status: TradeStatus
  planned_quantity: Decimal
  planned_entry_price: Decimal | null
  initial_stop_price: Decimal | null
  current_stop_price: Decimal | null
  targets: { sequence: number; price: Decimal; quantity: Decimal | null }[]
  executions: Execution[]
  thesis: string | null
  catalyst: string | null
  notes: string | null
  reflection: string | null
  created_at: string
  updated_at: string
}

export interface FillInput {
  price: Decimal
  executed_at: string // ISO with timezone
  quantity?: Decimal
  fees: Decimal
}

export interface TradeInput {
  portfolio_id: number
  instrument_id: number
  futures_contract_id: number | null
  strategy_id: number | null
  direction: Direction
  planned_quantity: Decimal
  planned_entry_price: Decimal | null
  initial_stop_price: Decimal | null
  current_stop_price: Decimal | null
  targets: { price: Decimal }[]
  thesis: string | null
  catalyst: string | null
  notes: string | null
  reflection: string | null
  entry: FillInput | null
  exit: FillInput | null
}

export interface TradeFilters {
  portfolio_id?: number
  status?: TradeStatus
  direction?: Direction
  q?: string
}
