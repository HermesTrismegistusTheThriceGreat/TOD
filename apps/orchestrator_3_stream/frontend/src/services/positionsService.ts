/**
 * Positions Service
 *
 * Service for fetching trading positions from the backend.
 * All requests include credential_id for account context.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:9403'

export interface Position {
  id: string
  symbol: string
  qty: string
  avg_entry_price: string
  market_value: string
  unrealized_pl: string
  unrealized_plpc: string
  current_price: string
  side: string
}

export interface PositionsResponse {
  status: 'success' | 'error'
  positions?: Position[]
  total_count?: number
  message?: string
}

export interface Order {
  id: string
  client_order_id: string
  symbol: string
  qty: string
  side: string
  type: string
  status: string
  filled_qty: string
  filled_avg_price: string
  created_at: string
  updated_at: string
  submitted_at: string
}

export interface OrdersResponse {
  status: 'success' | 'error'
  orders?: Order[]
  message?: string
}

/**
 * Fetch all positions for the given credential.
 *
 * @param credentialId - UUID of the credential to fetch positions for
 * @returns PositionsResponse with positions or error
 * @throws Error if credential_id is not provided
 */
export async function fetchPositions(credentialId: string): Promise<PositionsResponse> {
  if (!credentialId) {
    throw new Error('credential_id is required to fetch positions')
  }

  const url = new URL(`${API_BASE_URL}/api/positions`)
  url.searchParams.set('credential_id', credentialId)

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  })

  if (!response.ok) {
    if (response.status === 403) {
      throw new Error('Credential access denied')
    }
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.message || errorData.error || `HTTP ${response.status}`)
  }

  return response.json()
}

/**
 * Fetch a specific position by ID for the given credential.
 *
 * @param credentialId - UUID of the credential
 * @param positionId - ID of the position to fetch
 * @returns Position data or error
 */
export async function fetchPositionById(credentialId: string, positionId: string): Promise<PositionsResponse> {
  if (!credentialId) {
    throw new Error('credential_id is required to fetch position')
  }

  const url = new URL(`${API_BASE_URL}/api/positions/${positionId}`)
  url.searchParams.set('credential_id', credentialId)

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  })

  if (!response.ok) {
    if (response.status === 403) {
      throw new Error('Credential access denied')
    }
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.message || errorData.error || `HTTP ${response.status}`)
  }

  return response.json()
}

/**
 * Fetch orders for the given credential.
 *
 * @param credentialId - UUID of the credential to fetch orders for
 * @param status - Order status filter ('all', 'open', 'closed')
 * @param limit - Maximum number of orders to return
 * @returns Order list
 */
export async function fetchOrders(
  credentialId: string,
  status: 'all' | 'open' | 'closed' = 'all',
  limit: number = 100
): Promise<OrdersResponse> {
  if (!credentialId) {
    throw new Error('credential_id is required to fetch orders')
  }

  const url = new URL(`${API_BASE_URL}/api/orders`)
  url.searchParams.set('credential_id', credentialId)
  url.searchParams.set('status', status)
  url.searchParams.set('limit', limit.toString())

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  })

  if (!response.ok) {
    if (response.status === 403) {
      throw new Error('Credential access denied')
    }
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.message || errorData.error || `HTTP ${response.status}`)
  }

  return response.json()
}

export default {
  fetchPositions,
  fetchPositionById,
  fetchOrders
}
