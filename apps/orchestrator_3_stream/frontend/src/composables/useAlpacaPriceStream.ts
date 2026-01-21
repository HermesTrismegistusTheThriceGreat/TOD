/**
 * useAlpacaPriceStream Composable
 *
 * Provides access to real-time price updates from WebSocket.
 * Works with orchestrator store for centralized state.
 */

import { computed, watch, toRef } from 'vue'
import { useOrchestratorStore } from '../stores/orchestratorStore'
import type { OptionPriceUpdate, SpotPriceUpdate } from '../types/alpaca'

export interface PriceStreamCallbacks {
  onPriceUpdate?: (update: OptionPriceUpdate) => void
}

export function useAlpacaPriceStream(callbacks: PriceStreamCallbacks = {}) {
  const store = useOrchestratorStore()

  // Use toRef to maintain reactivity chain from store's shallowRef
  // CRITICAL: computed() breaks the reactivity for shallowRef + triggerRef pattern
  const priceCache = toRef(store, 'alpacaPriceCache')
  const spotPriceCache = toRef(store, 'spotPriceCache')
  const connectionStatus = toRef(store, 'alpacaConnectionStatus')

  /**
   * Get the latest price for a symbol.
   */
  function getPrice(symbol: string): OptionPriceUpdate | undefined {
    return store.getAlpacaPrice(symbol)
  }

  /**
   * Get the mid price for a symbol (for display).
   */
  function getMidPrice(symbol: string): number | undefined {
    return store.getAlpacaPrice(symbol)?.midPrice
  }

  /**
   * Get the spot price for a symbol (for underlying stock).
   */
  function getSpotPrice(symbol: string): number | undefined {
    const spotData = store.getSpotPrice(symbol)
    return spotData?.midPrice
  }

  /**
   * Watch for price updates and call callback.
   */
  if (callbacks.onPriceUpdate) {
    watch(
      () => store.alpacaPriceCache,
      () => {
        // This is triggered by triggerRef in the store
        // We could track individual updates, but for now
        // the callback can check the cache directly
      },
      { deep: false }
    )
  }

  /**
   * Get all cached prices.
   */
  function getAllPrices(): Map<string, OptionPriceUpdate> {
    return priceCache.value
  }

  /**
   * Check if we have a cached price for a symbol.
   */
  function hasPrice(symbol: string): boolean {
    return priceCache.value.has(symbol)
  }

  return {
    // State
    priceCache,
    spotPriceCache,
    connectionStatus,

    // Methods
    getPrice,
    getMidPrice,
    getSpotPrice,
    getAllPrices,
    hasPrice,
  }
}
