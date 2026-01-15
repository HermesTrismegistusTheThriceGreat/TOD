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
