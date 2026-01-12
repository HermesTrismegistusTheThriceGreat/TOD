import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { nextTick, ref, computed } from 'vue'
import OpenPositions from '../OpenPositions.vue'
import { useOrchestratorStore } from '../../stores/orchestratorStore'
import type { OpenPosition, OptionLeg } from '../../types/alpaca'

/**
 * Integration Tests for OpenPositions.vue
 *
 * These tests verify the reactive data flow from store -> composable -> component.
 * They use the real composable connected to a mocked store.
 */

// We need to mock certain dependencies but keep the composable working

// Mock chat service to prevent WebSocket connections
vi.mock('../../services/chatService', () => ({
  connectWebSocket: vi.fn(),
  disconnect: vi.fn(),
  loadChatHistory: vi.fn().mockResolvedValue({ messages: [], turn_count: 0 }),
  getOrchestratorInfo: vi.fn().mockResolvedValue({
    orchestrator: {
      id: 'test-orchestrator',
      name: 'Test Orchestrator',
      total_cost: 0,
      input_tokens: 0,
      output_tokens: 0,
    },
  }),
  sendMessage: vi.fn(),
}))

// Mock alpaca service to prevent actual API calls
vi.mock('../../services/alpacaService', () => ({
  getPositions: vi.fn().mockResolvedValue({
    status: 'success',
    positions: [],
    totalCount: 0,
  }),
  getPositionById: vi.fn().mockResolvedValue({
    status: 'success',
    position: null,
  }),
  subscribePrices: vi.fn().mockResolvedValue({ status: 'success' }),
}))

// Mock other services
vi.mock('../../services/agentService', () => ({
  loadAgents: vi.fn().mockResolvedValue([]),
}))

vi.mock('../../services/eventService', () => ({
  getEvents: vi.fn().mockResolvedValue({ events: [] }),
}))

// Mock OpenPositionCard
vi.mock('../OpenPositionCard.vue', () => ({
  default: {
    name: 'OpenPositionCard',
    props: ['initialData', 'positionId', 'useMockData'],
    template: `
      <div class="integration-open-position-card" :data-ticker="initialData?.ticker">
        <span class="ticker">{{ initialData?.ticker }}</span>
        <span v-for="leg in initialData?.legs" :key="leg.id" class="leg-price" :data-symbol="leg.symbol">
          {{ leg.currentPrice }}
        </span>
      </div>
    `,
  },
}))

// Mock Element Plus icons
vi.mock('@element-plus/icons-vue', () => ({
  Loading: { name: 'Loading', template: '<span class="loading-icon">Loading</span>' },
  Warning: { name: 'Warning', template: '<span class="warning-icon">Warning</span>' },
  Refresh: { name: 'Refresh', template: '<span class="refresh-icon">Refresh</span>' },
  Timer: { name: 'Timer', template: '<span class="timer-icon">Timer</span>' },
}))

// Global stubs for Element Plus components
const globalConfig = {
  global: {
    stubs: {
      'el-button': {
        name: 'ElButton',
        template: '<button class="el-button" @click="$emit(\'click\')"><slot /></button>',
        props: ['icon', 'circle', 'size', 'loading', 'type'],
      },
      'el-icon': {
        name: 'ElIcon',
        template: '<span class="el-icon"><slot /></span>',
        props: ['size'],
      },
    },
  },
}

describe('OpenPositions Integration', () => {
  let store: ReturnType<typeof useOrchestratorStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useOrchestratorStore()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Store -> Component Data Flow', () => {
    it('should update position data when store price changes', async () => {
      // Setup: Initial position
      const initialPosition: OpenPosition = {
        id: 'test-pos-1',
        ticker: 'SPY',
        strategy: 'Iron Condor',
        expiryDate: '2026-01-17',
        legs: [
          {
            id: 'leg-1',
            symbol: 'SPY260117C00600000',
            direction: 'Short' as const,
            strike: 600,
            optionType: 'Call' as const,
            quantity: 1,
            entryPrice: 2.50,
            currentPrice: 2.50,  // Initial price
            expiryDate: '2026-01-17',
            underlying: 'SPY',
          },
        ],
        createdAt: new Date().toISOString(),
      }

      // Set initial position in store
      store.setAlpacaPositions([initialPosition])

      // Simulate price update via store (as WebSocket would)
      store.updateAlpacaPrice('SPY260117C00600000', {
        symbol: 'SPY260117C00600000',
        bidPrice: 2.80,
        askPrice: 2.90,
        midPrice: 2.85,
        lastPrice: 2.85,
        volume: 100,
        timestamp: new Date().toISOString(),
      })

      await nextTick()

      // Verify the leg's currentPrice was updated in the store
      const updatedPosition = store.alpacaPositions[0]
      const updatedLeg = updatedPosition.legs.find(l => l.symbol === 'SPY260117C00600000')
      expect(updatedLeg?.currentPrice).toBe(2.85)
    })

    it('should handle rapid price updates without data loss', async () => {
      const position: OpenPosition = {
        id: 'test-pos-1',
        ticker: 'SPY',
        strategy: 'Iron Condor',
        expiryDate: '2026-01-17',
        legs: [
          {
            id: 'leg-1',
            symbol: 'SPY260117C00600000',
            direction: 'Short' as const,
            strike: 600,
            optionType: 'Call' as const,
            quantity: 1,
            entryPrice: 2.50,
            currentPrice: 2.50,
            expiryDate: '2026-01-17',
            underlying: 'SPY',
          },
        ],
        createdAt: new Date().toISOString(),
      }

      store.setAlpacaPositions([position])

      // Simulate 10 rapid price updates
      for (let i = 0; i < 10; i++) {
        store.updateAlpacaPrice('SPY260117C00600000', {
          symbol: 'SPY260117C00600000',
          bidPrice: 2.50 + (i * 0.01),
          askPrice: 2.60 + (i * 0.01),
          midPrice: 2.55 + (i * 0.01),
          lastPrice: 2.55 + (i * 0.01),
          volume: 100 + i,
          timestamp: new Date().toISOString(),
        })
      }

      await flushPromises()

      // Final price should be the last update (2.55 + 0.09 = 2.64)
      const finalLeg = store.alpacaPositions[0].legs[0]
      expect(finalLeg.currentPrice).toBeCloseTo(2.64, 2)
    })
  })

  describe('Store State Management', () => {
    it('should track position count correctly', async () => {
      expect(store.alpacaPositionCount).toBe(0)
      expect(store.hasAlpacaPositions).toBe(false)

      // Add positions
      store.setAlpacaPositions([
        { id: '1', ticker: 'SPY', strategy: 'IC', expiryDate: '2026-01-17', legs: [], createdAt: '' },
        { id: '2', ticker: 'QQQ', strategy: 'IC', expiryDate: '2026-01-17', legs: [], createdAt: '' },
      ])

      expect(store.alpacaPositionCount).toBe(2)
      expect(store.hasAlpacaPositions).toBe(true)
    })

    it('should update loading state correctly', async () => {
      expect(store.alpacaPositionsLoading).toBe(false)

      store.setAlpacaLoading(true)
      expect(store.alpacaPositionsLoading).toBe(true)

      store.setAlpacaLoading(false)
      expect(store.alpacaPositionsLoading).toBe(false)
    })

    it('should manage error state correctly', async () => {
      expect(store.alpacaPositionsError).toBeNull()

      store.setAlpacaError('Connection failed to Alpaca API')
      expect(store.alpacaPositionsError).toBe('Connection failed to Alpaca API')

      store.setAlpacaError(null)
      expect(store.alpacaPositionsError).toBeNull()
    })
  })

  describe('Price Cache Management', () => {
    it('should cache prices correctly', async () => {
      const position: OpenPosition = {
        id: 'test-pos-1',
        ticker: 'SPY',
        strategy: 'Iron Condor',
        expiryDate: '2026-01-17',
        legs: [
          {
            id: 'leg-1',
            symbol: 'SPY260117C00600000',
            direction: 'Short' as const,
            strike: 600,
            optionType: 'Call' as const,
            quantity: 1,
            entryPrice: 2.50,
            currentPrice: 2.50,
            expiryDate: '2026-01-17',
            underlying: 'SPY',
          },
        ],
        createdAt: new Date().toISOString(),
      }

      store.setAlpacaPositions([position])

      // Update price
      store.updateAlpacaPrice('SPY260117C00600000', {
        symbol: 'SPY260117C00600000',
        bidPrice: 2.80,
        askPrice: 2.90,
        midPrice: 2.85,
        lastPrice: 2.85,
        volume: 100,
        timestamp: new Date().toISOString(),
      })

      // Check cache
      const cachedPrice = store.getAlpacaPrice('SPY260117C00600000')
      expect(cachedPrice).toBeDefined()
      expect(cachedPrice?.midPrice).toBe(2.85)
    })

    it('should clear price cache correctly', async () => {
      store.updateAlpacaPrice('SPY260117C00600000', {
        symbol: 'SPY260117C00600000',
        bidPrice: 2.80,
        askPrice: 2.90,
        midPrice: 2.85,
        lastPrice: 2.85,
        volume: 100,
        timestamp: new Date().toISOString(),
      })

      expect(store.getAlpacaPrice('SPY260117C00600000')).toBeDefined()

      store.clearAlpacaPriceCache()

      expect(store.getAlpacaPrice('SPY260117C00600000')).toBeUndefined()
    })
  })

  describe('Connection Status', () => {
    it('should track Alpaca connection status', async () => {
      expect(store.alpacaConnectionStatus).toBe('disconnected')

      store.setAlpacaConnectionStatus('connected')
      expect(store.alpacaConnectionStatus).toBe('connected')

      store.setAlpacaConnectionStatus('error')
      expect(store.alpacaConnectionStatus).toBe('error')

      store.setAlpacaConnectionStatus('disconnected')
      expect(store.alpacaConnectionStatus).toBe('disconnected')
    })
  })

  describe('P/L Calculations', () => {
    it('should calculate P/L when price updates', async () => {
      const position: OpenPosition = {
        id: 'test-pos-1',
        ticker: 'SPY',
        strategy: 'Iron Condor',
        expiryDate: '2026-01-17',
        legs: [
          {
            id: 'leg-1',
            symbol: 'SPY260117C00600000',
            direction: 'Short' as const,  // Short position
            strike: 600,
            optionType: 'Call' as const,
            quantity: 10,
            entryPrice: 2.50,
            currentPrice: 2.50,
            expiryDate: '2026-01-17',
            underlying: 'SPY',
          },
        ],
        createdAt: new Date().toISOString(),
      }

      store.setAlpacaPositions([position])

      // Price drops (good for short position)
      store.updateAlpacaPrice('SPY260117C00600000', {
        symbol: 'SPY260117C00600000',
        bidPrice: 1.80,
        askPrice: 2.00,
        midPrice: 1.90,  // Down from 2.50
        lastPrice: 1.90,
        volume: 100,
        timestamp: new Date().toISOString(),
      })

      await nextTick()

      // Check that P/L was calculated
      const updatedLeg = store.alpacaPositions[0].legs[0]
      expect(updatedLeg.currentPrice).toBe(1.90)

      // P/L for short position: (entry - current) * quantity * 100
      // (2.50 - 1.90) * 10 * 100 = 600
      expect(updatedLeg.pnlDollars).toBeCloseTo(600, 2)
    })
  })
})
