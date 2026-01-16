/**
 * Trade History Type Definitions
 *
 * Types for trade history data from the backend API.
 * These match the Pydantic models in backend/modules/alpaca_models.py
 */

/**
 * Order detail for individual legs within a trade
 */
export interface OrderDetail {
  order_id: string
  symbol: string
  side: 'buy' | 'sell'
  qty: number
  filled_qty: number
  filled_avg_price: number | null
  status: string
  submitted_at: string | null
  filled_at: string | null
  option_type: 'call' | 'put' | null
  strike_price: number | null
  expiry_date: string | null
}

export interface Trade {
  trade_id: string
  ticker: string
  strategy: string
  direction: 'Long' | 'Short'
  entry_date: string
  exit_date: string | null
  entry_price: number
  exit_price: number | null
  quantity: number
  pnl: number
  pnl_percent: number
  status: 'open' | 'closed' | 'expired'
  leg_count: number
  orders: OrderDetail[]
}

export interface TradeListResponse {
  status: 'success' | 'error'
  trades: Trade[]
  total_count: number
  message?: string
}

export interface TradeStats {
  total_pnl: number
  win_rate: number
  total_trades: number
  winning_trades: number
  losing_trades: number
  open_trades: number
  closed_trades: number
}

/**
 * Discriminated union for TradeStatsResponse
 * Success response has all numeric fields required, error response has message
 */
export type TradeStatsResponse = TradeStatsSuccessResponse | TradeStatsErrorResponse

export interface TradeStatsSuccessResponse {
  status: 'success'
  total_pnl: number
  win_rate: number
  total_trades: number
  winning_trades: number
  losing_trades: number
  open_trades: number
  closed_trades: number
}

export interface TradeStatsErrorResponse {
  status: 'error'
  message: string
}

/**
 * Individual leg with open/close matching
 */
export interface LegDetail {
  leg_number: number
  description: string  // e.g., "423 Call"
  symbol: string
  strike: number
  option_type: 'call' | 'put'

  // Open (entry) details
  open_action: 'BUY' | 'SELL'
  open_fill: number
  open_date: string | null

  // Close (exit) details
  close_action: 'BUY' | 'SELL' | null
  close_fill: number | null
  close_date: string | null

  // P&L
  quantity: number
  pnl_per_contract: number
  pnl_total: number
  is_closed: boolean
}

/**
 * Aggregated summary for all legs in a trade
 */
export interface TradeSummary {
  opening_credit: number    // Net credit received at open
  closing_debit: number     // Net debit paid at close
  net_pnl_per_contract: number
  net_pnl_total: number
  leg_count: number
  closed_legs: number
  open_legs: number
}

/**
 * Complete trade with leg-level detail
 */
export interface DetailedTrade {
  trade_id: string
  ticker: string
  strategy: string
  direction: 'Long' | 'Short'
  status: 'open' | 'closed' | 'partial'
  entry_date: string
  exit_date: string | null
  expiry_date: string | null
  legs: LegDetail[]
  summary: TradeSummary
}

export interface DetailedTradeListResponse {
  status: 'success' | 'error'
  trades: DetailedTrade[]
  total_count: number
  message?: string
}
