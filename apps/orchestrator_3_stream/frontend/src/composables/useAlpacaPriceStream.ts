/**
 * useAlpacaPriceStream Composable
 *
 * Provides access to real-time price updates from WebSocket.
 * Works with orchestrator store for centralized state.
 */

import { computed, watch } from 'vue'
import { useOrchestratorStore } from '../stores/orchestratorStore'
import type { OptionPriceUpdate } from '../types/alpaca'

export interface PriceStreamCallbacks {
  onPriceUpdate?: (update: OptionPriceUpdate) => void
}

export function useAlpacaPriceStream(callbacks: PriceStreamCallbacks = {}) {
  const store = useOrchestratorStore()

  // Computed from store
  const priceCache = computed(() => store.alpacaPriceCache)
  const connectionStatus = computed(() => store.alpacaConnectionStatus)

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
    connectionStatus,

    // Methods
    getPrice,
    getMidPrice,
    getAllPrices,
    hasPrice,
  }
}
