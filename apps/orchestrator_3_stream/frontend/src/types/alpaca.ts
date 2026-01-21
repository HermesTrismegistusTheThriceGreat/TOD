/**
 * Alpaca Trading API TypeScript Interfaces
 *
 * Pattern: Raw* types match backend snake_case, then transform to camelCase.
 * This solves the snake_case → camelCase mismatch between Python and TypeScript.
 */

// ═══════════════════════════════════════════════════════════
// RAW TYPES (Backend snake_case)
// ═══════════════════════════════════════════════════════════

/** Raw option leg from backend (snake_case) */
export interface RawOptionLeg {
  id: string
  symbol: string
  direction: 'Long' | 'Short'
  strike: number
  option_type: 'Call' | 'Put'
  quantity: number
  entry_price: number
  current_price: number
  expiry_date: string
  underlying: string
  pnl_dollars?: number
  pnl_percent?: number
}

/** Raw open position from backend (snake_case) */
export interface RawOpenPosition {
  id: string
  ticker: string
  strategy: string
  expiry_date: string
  legs: RawOptionLeg[]
  created_at: string
  total_pnl?: number
  days_to_expiry?: number
  spot_price?: number
}

/** Raw price update from backend (snake_case) */
export interface RawOptionPriceUpdate {
  symbol: string
  bid_price: number
  ask_price: number
  mid_price: number
  last_price?: number
  volume: number
  timestamp: string
}

/** Raw spot price update from backend (snake_case) */
export interface RawSpotPriceUpdate {
  symbol: string
  bid_price: number
  ask_price: number
  mid_price: number
  last_price?: number
  timestamp: string
}

/** Raw API response for positions */
export interface RawGetPositionsResponse {
  status: 'success' | 'error'
  positions: RawOpenPosition[]
  total_count: number
  message?: string
}

/** Raw API response for single position */
export interface RawGetPositionResponse {
  status: 'success' | 'error'
  position?: RawOpenPosition
  message?: string
}

/** Raw close order result from backend (snake_case) */
export interface RawCloseOrderResult {
  symbol: string
  order_id: string
  status: 'submitted' | 'filled' | 'failed'
  filled_qty: number
  filled_avg_price?: number
  error_message?: string
}

/** Raw close strategy response from backend (snake_case) */
export interface RawCloseStrategyResponse {
  status: 'success' | 'partial' | 'error'
  position_id: string
  orders: RawCloseOrderResult[]
  message?: string
  total_legs: number
  closed_legs: number
}

/** Raw close leg response from backend (snake_case) */
export interface RawCloseLegResponse {
  status: 'success' | 'error'
  order?: RawCloseOrderResult
  message?: string
}

// ═══════════════════════════════════════════════════════════
// FRONTEND TYPES (camelCase)
// ═══════════════════════════════════════════════════════════

/** Option leg (frontend camelCase) */
export interface OptionLeg {
  id: string
  symbol: string
  direction: 'Long' | 'Short'
  strike: number
  optionType: 'Call' | 'Put'
  quantity: number
  entryPrice: number
  currentPrice: number
  expiryDate: string
  underlying: string
  pnlDollars?: number
  pnlPercent?: number
}

/** Open position (frontend camelCase) */
export interface OpenPosition {
  id: string
  ticker: string
  strategy: string
  expiryDate: string
  legs: OptionLeg[]
  createdAt: string
  totalPnl?: number
  daysToExpiry?: number
  spotPrice?: number
}

/** Option price update (frontend camelCase) */
export interface OptionPriceUpdate {
  symbol: string
  bidPrice: number
  askPrice: number
  midPrice: number
  lastPrice?: number
  volume: number
  timestamp: string
}

/** Spot price update (frontend camelCase) */
export interface SpotPriceUpdate {
  symbol: string
  bidPrice: number
  askPrice: number
  midPrice: number
  lastPrice?: number
  timestamp: string
}

/** API response for positions (frontend) */
export interface GetPositionsResponse {
  status: 'success' | 'error'
  positions: OpenPosition[]
  totalCount: number
  message?: string
}

/** API response for single position (frontend) */
export interface GetPositionResponse {
  status: 'success' | 'error'
  position?: OpenPosition
  message?: string
}

/** Request for subscribing to prices */
export interface SubscribePricesRequest {
  symbols: string[]
}

/** Close order result (frontend camelCase) */
export interface CloseOrderResult {
  symbol: string
  orderId: string
  status: 'submitted' | 'filled' | 'failed'
  filledQty: number
  filledAvgPrice?: number
  errorMessage?: string
}

/** Close strategy response (frontend camelCase) */
export interface CloseStrategyResponse {
  status: 'success' | 'partial' | 'error'
  positionId: string
  orders: CloseOrderResult[]
  message?: string
  totalLegs: number
  closedLegs: number
}

/** Close leg response (frontend camelCase) */
export interface CloseLegResponse {
  status: 'success' | 'error'
  order?: CloseOrderResult
  message?: string
}

// ═══════════════════════════════════════════════════════════
// TRANSFORM FUNCTIONS (snake_case → camelCase)
// ═══════════════════════════════════════════════════════════

/**
 * Transform raw option leg from backend to frontend format.
 */
export function transformOptionLeg(raw: RawOptionLeg): OptionLeg {
  return {
    id: raw.id,
    symbol: raw.symbol,
    direction: raw.direction,
    strike: raw.strike,
    optionType: raw.option_type,
    quantity: raw.quantity,
    entryPrice: raw.entry_price,
    currentPrice: raw.current_price,
    expiryDate: raw.expiry_date,
    underlying: raw.underlying,
    pnlDollars: raw.pnl_dollars,
    pnlPercent: raw.pnl_percent,
  }
}

/**
 * Transform raw position from backend to frontend format.
 */
export function transformPosition(raw: RawOpenPosition): OpenPosition {
  return {
    id: raw.id,
    ticker: raw.ticker,
    strategy: raw.strategy,
    expiryDate: raw.expiry_date,
    legs: raw.legs.map(transformOptionLeg),
    createdAt: raw.created_at,
    totalPnl: raw.total_pnl,
    daysToExpiry: raw.days_to_expiry,
    spotPrice: raw.spot_price,
  }
}

/**
 * Transform raw price update from backend to frontend format.
 */
export function transformPriceUpdate(raw: RawOptionPriceUpdate): OptionPriceUpdate {
  return {
    symbol: raw.symbol,
    bidPrice: raw.bid_price,
    askPrice: raw.ask_price,
    midPrice: raw.mid_price,
    lastPrice: raw.last_price,
    volume: raw.volume,
    timestamp: raw.timestamp,
  }
}

/**
 * Transform raw spot price update from backend to frontend format.
 */
export function transformSpotPriceUpdate(raw: RawSpotPriceUpdate): SpotPriceUpdate {
  return {
    symbol: raw.symbol,
    bidPrice: raw.bid_price,
    askPrice: raw.ask_price,
    midPrice: raw.mid_price,
    lastPrice: raw.last_price,
    timestamp: raw.timestamp,
  }
}

/**
 * Transform raw positions response from backend.
 */
export function transformPositionsResponse(raw: RawGetPositionsResponse): GetPositionsResponse {
  return {
    status: raw.status,
    positions: raw.positions.map(transformPosition),
    totalCount: raw.total_count,
    message: raw.message,
  }
}

/**
 * Transform raw position response from backend.
 */
export function transformPositionResponse(raw: RawGetPositionResponse): GetPositionResponse {
  return {
    status: raw.status,
    position: raw.position ? transformPosition(raw.position) : undefined,
    message: raw.message,
  }
}

/**
 * Transform raw close order result from backend.
 */
export function transformCloseOrderResult(raw: RawCloseOrderResult): CloseOrderResult {
  return {
    symbol: raw.symbol,
    orderId: raw.order_id,
    status: raw.status,
    filledQty: raw.filled_qty,
    filledAvgPrice: raw.filled_avg_price,
    errorMessage: raw.error_message,
  }
}

/**
 * Transform raw close strategy response from backend.
 */
export function transformCloseStrategyResponse(raw: RawCloseStrategyResponse): CloseStrategyResponse {
  return {
    status: raw.status,
    positionId: raw.position_id,
    orders: raw.orders.map(transformCloseOrderResult),
    message: raw.message,
    totalLegs: raw.total_legs,
    closedLegs: raw.closed_legs,
  }
}

/**
 * Transform raw close leg response from backend.
 */
export function transformCloseLegResponse(raw: RawCloseLegResponse): CloseLegResponse {
  return {
    status: raw.status,
    order: raw.order ? transformCloseOrderResult(raw.order) : undefined,
    message: raw.message,
  }
}

// ═══════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════

/**
 * Calculate P/L for a leg (for local recalculation after price updates)
 */
export function calculateLegPnl(leg: OptionLeg): { dollars: number; percent: number } {
  const multiplier = leg.direction === 'Short' ? 1 : -1
  const priceDiff = (leg.entryPrice - leg.currentPrice) * multiplier
  const dollars = priceDiff * leg.quantity * 100

  let percent = 0
  if (leg.entryPrice !== 0) {
    const directionMult = leg.direction === 'Short' ? -1 : 1
    percent = ((leg.currentPrice - leg.entryPrice) / leg.entryPrice) * 100 * directionMult
  }

  return { dollars, percent }
}

/**
 * Extract all option symbols from positions for price subscription.
 */
export function extractSymbolsFromPositions(positions: OpenPosition[]): string[] {
  const symbols: string[] = []

  for (const position of positions) {
    for (const leg of position.legs) {
      if (leg.symbol && symbols.indexOf(leg.symbol) === -1) {
        symbols.push(leg.symbol)
      }
    }
  }

  return symbols
}

/**
 * Extract unique underlying tickers from positions for spot price subscription.
 */
export function extractUnderlyingTickersFromPositions(positions: OpenPosition[]): string[] {
  const tickers: string[] = []

  for (const position of positions) {
    if (position.ticker && tickers.indexOf(position.ticker) === -1) {
      tickers.push(position.ticker)
    }
  }

  return tickers
}

// ═══════════════════════════════════════════════════════════
// TYPE ALIASES
// ═══════════════════════════════════════════════════════════

/** Ticker position (alias for backwards compatibility) */
export type TickerPosition = OpenPosition
