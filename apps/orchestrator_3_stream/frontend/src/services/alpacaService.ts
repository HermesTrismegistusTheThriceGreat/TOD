/**
 * Alpaca REST API Service
 *
 * Client for Alpaca trading endpoints.
 */

import { apiClient } from './api'
import type {
  RawGetPositionsResponse,
  RawGetPositionResponse,
  RawCloseStrategyResponse,
  RawCloseLegResponse,
  GetPositionsResponse,
  GetPositionResponse,
  CloseStrategyResponse,
  CloseLegResponse,
  SubscribePricesRequest,
} from '../types/alpaca'
import {
  transformPositionsResponse,
  transformPositionResponse,
  transformCloseStrategyResponse,
  transformCloseLegResponse,
} from '../types/alpaca'

// Raw circuit status from API (snake_case)
export interface RawCircuitStatus {
  status: string
  circuit_state: string
  is_configured: boolean
}

// Transformed circuit status (camelCase)
export interface CircuitStatus {
  status: string
  circuitState: string
  isConfigured: boolean
}

function transformCircuitStatus(raw: RawCircuitStatus): CircuitStatus {
  return {
    status: raw.status,
    circuitState: raw.circuit_state,
    isConfigured: raw.is_configured,
  }
}

/**
 * Fetch all open positions from Alpaca.
 * @param credentialId - Optional credential ID for user-specific positions
 */
export async function getPositions(credentialId?: string): Promise<GetPositionsResponse> {
  const params = credentialId ? { credential_id: credentialId } : {}
  const response = await apiClient.get<RawGetPositionsResponse>('/api/positions', { params })
  return transformPositionsResponse(response.data)
}

/**
 * Fetch a specific position by ID.
 * @param positionId - The position ID to fetch
 * @param credentialId - Optional credential ID for user-specific positions
 */
export async function getPositionById(positionId: string, credentialId?: string): Promise<GetPositionResponse> {
  const params = credentialId ? { credential_id: credentialId } : {}
  const response = await apiClient.get<RawGetPositionResponse>(`/api/positions/${positionId}`, { params })
  return transformPositionResponse(response.data)
}

/**
 * Subscribe to real-time price updates for option symbols.
 */
export async function subscribePrices(symbols: string[]): Promise<void> {
  await apiClient.post('/api/positions/subscribe-prices', {
    symbols
  } as SubscribePricesRequest)
}

/**
 * Subscribe to real-time spot price updates for underlying symbols.
 */
export async function subscribeSpotPrices(symbols: string[]): Promise<void> {
  await apiClient.post('/api/positions/subscribe-spot-prices', {
    symbols
  })
}

/**
 * Get circuit breaker status.
 */
export async function getCircuitStatus(): Promise<CircuitStatus> {
  const response = await apiClient.get<RawCircuitStatus>('/api/positions/circuit-status')
  return transformCircuitStatus(response.data)
}

/**
 * Close an entire strategy (all legs) for a position.
 */
export async function closeStrategy(
  positionId: string,
  orderType: 'market' | 'limit' = 'market'
): Promise<CloseStrategyResponse> {
  const response = await apiClient.post<RawCloseStrategyResponse>(
    `/api/positions/${positionId}/close-strategy`,
    { position_id: positionId, order_type: orderType }
  )
  return transformCloseStrategyResponse(response.data)
}

/**
 * Close a single leg of a position.
 */
export async function closeLeg(
  positionId: string,
  legId: string,
  orderType: 'market' | 'limit' = 'market',
  limitPrice?: number
): Promise<CloseLegResponse> {
  const response = await apiClient.post<RawCloseLegResponse>(
    `/api/positions/${positionId}/close-leg`,
    {
      leg_id: legId,
      order_type: orderType,
      limit_price: limitPrice
    }
  )
  return transformCloseLegResponse(response.data)
}
