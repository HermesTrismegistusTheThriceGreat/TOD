/**
 * useAlpacaPositions Composable
 *
 * Manages fetching and state of open positions.
 * Integrates with orchestrator store for WebSocket updates.
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useOrchestratorStore } from '../stores/orchestratorStore'
import type { OpenPosition } from '../types/alpaca'
import { extractSymbolsFromPositions, extractUnderlyingTickersFromPositions } from '../types/alpaca'
import * as alpacaService from '../services/alpacaService'

export interface UseAlpacaPositionsOptions {
  /** Auto-fetch positions on mount */
  autoFetch?: boolean
  /** Auto-subscribe to price updates after fetching */
  autoSubscribe?: boolean
  /** Specific position ID to fetch (for single position view) */
  positionId?: string
}

export function useAlpacaPositions(options: UseAlpacaPositionsOptions = {}) {
  const {
    autoFetch = true,
    autoSubscribe = true,
    positionId = undefined
  } = options

  const store = useOrchestratorStore()

  // Local state
  const isSubscribed = ref(false)
  const localError = ref<string | null>(null)

  // Computed from store
  const positions = computed(() => store.alpacaPositions)
  const loading = computed(() => store.alpacaPositionsLoading)
  const error = computed(() => store.alpacaPositionsError || localError.value)
  const hasPositions = computed(() => store.hasAlpacaPositions)
  const positionCount = computed(() => store.alpacaPositionCount)

  // Get current position (for single position mode)
  const currentPosition = computed<OpenPosition | null>(() => {
    if (positionId) {
      return store.getAlpacaPositionById(positionId) || null
    }
    return positions.value.length > 0 ? positions.value[0] : null
  })

  /**
   * Fetch all positions from Alpaca API.
   */
  async function fetchPositions(): Promise<void> {
    store.setAlpacaLoading(true)
    store.setAlpacaError(null)
    localError.value = null

    try {
      const response = await alpacaService.getPositions()

      if (response.status === 'error') {
        throw new Error(response.message || 'Failed to fetch positions')
      }

      store.setAlpacaPositions(response.positions)

      // Auto-subscribe to price updates
      if (autoSubscribe && response.positions.length > 0) {
        await subscribeToUpdates()
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to fetch positions'
      store.setAlpacaError(message)
      console.error('useAlpacaPositions.fetchPositions error:', e)
    } finally {
      store.setAlpacaLoading(false)
    }
  }

  /**
   * Fetch a specific position by ID.
   */
  async function fetchPosition(id: string): Promise<void> {
    store.setAlpacaLoading(true)
    store.setAlpacaError(null)

    try {
      const response = await alpacaService.getPositionById(id)

      if (response.status === 'error') {
        throw new Error(response.message || 'Failed to fetch position')
      }

      if (response.position) {
        // Add or update in positions array
        const index = store.alpacaPositions.findIndex(p => p.id === id)
        if (index >= 0) {
          store.alpacaPositions[index] = response.position
        } else {
          store.alpacaPositions.push(response.position)
        }

        // Subscribe to price updates for this position
        if (autoSubscribe) {
          const symbols = extractSymbolsFromPositions([response.position])
          await alpacaService.subscribePrices(symbols)

          const underlyingTickers = extractUnderlyingTickersFromPositions([response.position])
          if (underlyingTickers.length > 0) {
            await alpacaService.subscribeSpotPrices(underlyingTickers)
          }

          isSubscribed.value = true
        }
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to fetch position'
      store.setAlpacaError(message)
      console.error('useAlpacaPositions.fetchPosition error:', e)
    } finally {
      store.setAlpacaLoading(false)
    }
  }

  /**
   * Subscribe to price updates for all position symbols.
   */
  async function subscribeToUpdates(): Promise<void> {
    if (isSubscribed.value) return

    try {
      // Subscribe to option prices
      const symbols = extractSymbolsFromPositions(positions.value)

      if (symbols.length > 0) {
        await alpacaService.subscribePrices(symbols)
        console.log(`Subscribed to ${symbols.length} option symbols`)
      }

      // Subscribe to spot prices for underlying tickers
      const underlyingTickers = extractUnderlyingTickersFromPositions(positions.value)

      if (underlyingTickers.length > 0) {
        await alpacaService.subscribeSpotPrices(underlyingTickers)
        console.log(`Subscribed to ${underlyingTickers.length} spot price symbols: ${underlyingTickers.join(', ')}`)
      }

      isSubscribed.value = true
    } catch (e) {
      console.error('Failed to subscribe to price updates:', e)
      // Non-critical error, don't set error state
    }
  }

  /**
   * Refresh positions (re-fetch from API).
   */
  async function refresh(): Promise<void> {
    if (positionId) {
      await fetchPosition(positionId)
    } else {
      await fetchPositions()
    }
  }

  /**
   * Get cached price for a symbol.
   */
  function getCachedPrice(symbol: string) {
    return store.getAlpacaPrice(symbol)
  }

  /**
   * Handle WebSocket reconnection event.
   * Reset subscription state and re-subscribe to price updates.
   */
  function handleReconnect() {
    console.log('WebSocket reconnected, re-subscribing to price updates')
    isSubscribed.value = false
    subscribeToUpdates()
  }

  // Lifecycle
  onMounted(() => {
    if (autoFetch) {
      if (positionId) {
        fetchPosition(positionId).catch(e => {
          console.error('Error fetching position on mount:', e)
        })
      } else {
        fetchPositions().catch(e => {
          console.error('Error fetching positions on mount:', e)
        })
      }
    }

    // Listen for reconnection events to re-subscribe
    window.addEventListener('alpaca-reconnect', handleReconnect)
  })

  onUnmounted(() => {
    window.removeEventListener('alpaca-reconnect', handleReconnect)
  })

  return {
    // State
    positions,
    currentPosition,
    loading,
    error,
    isSubscribed,

    // Computed
    hasPositions,
    positionCount,

    // Actions
    fetchPositions,
    fetchPosition,
    subscribeToUpdates,
    refresh,
    getCachedPrice,
  }
}
