import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAlpacaPositions } from '../useAlpacaPositions'
import * as alpacaService from '../../services/alpacaService'

// Mock the service
vi.mock('../../services/alpacaService')

describe('useAlpacaPositions', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('initialization', () => {
    it('should initialize with default values', () => {
      vi.mocked(alpacaService.getPositions).mockResolvedValue({
        status: 'success',
        positions: [],
        totalCount: 0,
      })

      const { positions, loading, error, hasPositions } = useAlpacaPositions({
        autoFetch: false,
      })

      expect(positions.value).toEqual([])
      expect(loading.value).toBe(false)
      expect(error.value).toBeNull()
      expect(hasPositions.value).toBe(false)
    })
  })

  describe('fetchPositions', () => {
    it('should fetch and set positions', async () => {
      const mockPositions = [
        {
          id: 'test-1',
          ticker: 'SPY',
          strategy: 'Options',
          expiryDate: '2026-01-17',
          legs: [],
          createdAt: new Date().toISOString(),
        },
      ]

      vi.mocked(alpacaService.getPositions).mockResolvedValue({
        status: 'success',
        positions: mockPositions,
        totalCount: 1,
      })

      vi.mocked(alpacaService.subscribePrices).mockResolvedValue()

      const { positions, fetchPositions, hasPositions } = useAlpacaPositions({
        autoFetch: false,
      })

      await fetchPositions()

      expect(positions.value).toHaveLength(1)
      expect(positions.value[0].ticker).toBe('SPY')
      expect(hasPositions.value).toBe(true)
    })

    it('should handle errors', async () => {
      vi.mocked(alpacaService.getPositions).mockResolvedValue({
        status: 'error',
        positions: [],
        totalCount: 0,
        message: 'API error',
      })

      const { error, fetchPositions } = useAlpacaPositions({
        autoFetch: false,
      })

      await fetchPositions()

      expect(error.value).toBe('API error')
    })
  })

  describe('fetchPosition', () => {
    it('should fetch and set a single position', async () => {
      const mockPosition = {
        id: 'test-1',
        ticker: 'SPY',
        strategy: 'Options',
        expiryDate: '2026-01-17',
        legs: [{
          id: 'leg-1',
          symbol: 'SPY260117C00688000',
          direction: 'Short' as const,
          strike: 688,
          optionType: 'Call' as const,
          quantity: 10,
          entryPrice: 4.0,
          currentPrice: 3.5,
          expiryDate: '2026-01-17',
          underlying: 'SPY',
        }],
        createdAt: new Date().toISOString(),
      }

      vi.mocked(alpacaService.getPositionById).mockResolvedValue({
        status: 'success',
        position: mockPosition,
      })
      vi.mocked(alpacaService.subscribePrices).mockResolvedValue()

      const { fetchPosition } = useAlpacaPositions({ autoFetch: false })

      await fetchPosition('test-1')

      expect(alpacaService.getPositionById).toHaveBeenCalledWith('test-1')
    })
  })

  describe('refresh', () => {
    it('should re-fetch all positions', async () => {
      const mockPositions = [{
        id: 'test-1',
        ticker: 'SPY',
        strategy: 'Options',
        expiryDate: '2026-01-17',
        legs: [],
        createdAt: new Date().toISOString(),
      }]

      vi.mocked(alpacaService.getPositions).mockResolvedValue({
        status: 'success',
        positions: mockPositions,
        totalCount: 1,
      })
      vi.mocked(alpacaService.subscribePrices).mockResolvedValue()

      const { refresh } = useAlpacaPositions({ autoFetch: false })

      await refresh()

      expect(alpacaService.getPositions).toHaveBeenCalled()
    })
  })

  describe('subscribeToUpdates', () => {
    it('should subscribe to price updates', async () => {
      const mockPositions = [
        {
          id: 'test-1',
          ticker: 'SPY',
          strategy: 'Options',
          expiryDate: '2026-01-17',
          legs: [
            {
              id: 'leg-1',
              symbol: 'SPY260117C00688000',
              direction: 'Short' as const,
              strike: 688,
              optionType: 'Call' as const,
              quantity: 10,
              entryPrice: 4.0,
              currentPrice: 3.5,
              expiryDate: '2026-01-17',
              underlying: 'SPY',
            },
          ],
          createdAt: new Date().toISOString(),
        },
      ]

      vi.mocked(alpacaService.getPositions).mockResolvedValue({
        status: 'success',
        positions: mockPositions,
        totalCount: 1,
      })

      vi.mocked(alpacaService.subscribePrices).mockResolvedValue()

      const { fetchPositions, isSubscribed } = useAlpacaPositions({
        autoFetch: false,
        autoSubscribe: true,
      })

      await fetchPositions()

      expect(alpacaService.subscribePrices).toHaveBeenCalledWith(['SPY260117C00688000'])
      expect(isSubscribed.value).toBe(true)
    })
  })
})
