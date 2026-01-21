import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { ref, computed } from 'vue'
import OpenPositions from '../OpenPositions.vue'
import type { OpenPosition } from '../../types/alpaca'

// Mock useAlpacaPositions composable - must be before imports
const mockPositions = ref<OpenPosition[]>([])
const mockLoading = ref(false)
const mockError = ref<string | null>(null)
const mockHasPositions = computed(() => mockPositions.value.length > 0)
const mockPositionCount = computed(() => mockPositions.value.length)
const mockRefresh = vi.fn()

vi.mock('../../composables/useAlpacaPositions', () => ({
  useAlpacaPositions: () => ({
    positions: mockPositions,
    loading: mockLoading,
    error: mockError,
    hasPositions: mockHasPositions,
    positionCount: mockPositionCount,
    refresh: mockRefresh,
  }),
}))

// Mock OpenPositionCard
vi.mock('../OpenPositionCard.vue', () => ({
  default: {
    name: 'OpenPositionCard',
    props: ['initialData', 'positionId', 'useMockData'],
    template: '<div class="mock-open-position-card" :data-ticker="initialData?.ticker">{{ initialData?.ticker }}</div>',
  },
}))

// Mock Element Plus icons
vi.mock('@element-plus/icons-vue', () => ({
  Loading: { name: 'Loading', template: '<span class="loading-icon">Loading</span>' },
  Warning: { name: 'Warning', template: '<span class="warning-icon">Warning</span>' },
  Refresh: { name: 'Refresh', template: '<span class="refresh-icon">Refresh</span>' },
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

describe('OpenPositions.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockPositions.value = []
    mockLoading.value = false
    mockError.value = null
  })

  describe('Loading State', () => {
    it('should show loading state when loading and no positions', async () => {
      mockLoading.value = true
      mockPositions.value = []

      const wrapper = mount(OpenPositions, globalConfig)

      expect(wrapper.find('.loading-state').exists()).toBe(true)
      expect(wrapper.text()).toContain('Loading positions from Alpaca')
    })

    it('should show positions grid while refreshing with existing data', async () => {
      mockLoading.value = true
      mockPositions.value = [
        {
          id: 'test-1',
          ticker: 'SPY',
          strategy: 'Options',
          expiryDate: '2026-01-17',
          legs: [],
          createdAt: new Date().toISOString(),
        },
      ]

      const wrapper = mount(OpenPositions, globalConfig)

      // Should show grid, not loading state (background refresh)
      expect(wrapper.find('.loading-state').exists()).toBe(false)
      expect(wrapper.find('.positions-grid').exists()).toBe(true)
    })
  })

  describe('Error State', () => {
    it('should show error state with message', async () => {
      mockError.value = 'Failed to connect to Alpaca'

      const wrapper = mount(OpenPositions, globalConfig)

      expect(wrapper.find('.error-state').exists()).toBe(true)
      expect(wrapper.text()).toContain('Failed to connect to Alpaca')
    })

    it('should call refresh when retry button clicked', async () => {
      mockError.value = 'Network error'

      const wrapper = mount(OpenPositions, globalConfig)
      const retryButton = wrapper.find('.error-state .el-button')
      expect(retryButton.exists()).toBe(true)
      await retryButton.trigger('click')

      expect(mockRefresh).toHaveBeenCalled()
    })
  })

  describe('Empty State', () => {
    it('should show empty state when no positions', async () => {
      mockLoading.value = false
      mockError.value = null
      mockPositions.value = []

      const wrapper = mount(OpenPositions, globalConfig)

      expect(wrapper.find('.empty-state').exists()).toBe(true)
      expect(wrapper.text()).toContain('No open option positions')
    })

    it('should call refresh when check again clicked', async () => {
      mockPositions.value = []

      const wrapper = mount(OpenPositions, globalConfig)
      const checkAgainButton = wrapper.find('.empty-state .el-button')
      expect(checkAgainButton.exists()).toBe(true)
      await checkAgainButton.trigger('click')

      expect(mockRefresh).toHaveBeenCalled()
    })
  })

  describe('Positions Grid', () => {
    it('should render OpenPositionCard for each position', async () => {
      mockPositions.value = [
        {
          id: 'pos-1',
          ticker: 'SPY',
          strategy: 'Options',
          expiryDate: '2026-01-17',
          legs: [],
          createdAt: new Date().toISOString(),
        },
        {
          id: 'pos-2',
          ticker: 'QQQ',
          strategy: 'Options',
          expiryDate: '2026-01-24',
          legs: [],
          createdAt: new Date().toISOString(),
        },
      ]

      const wrapper = mount(OpenPositions, globalConfig)

      const cards = wrapper.findAll('.mock-open-position-card')
      expect(cards).toHaveLength(2)
      expect(cards[0].text()).toBe('SPY')
      expect(cards[1].text()).toBe('QQQ')
    })

    it('should show correct position count in header', async () => {
      mockPositions.value = [
        { id: '1', ticker: 'SPY', strategy: 'IC', expiryDate: '2026-01-17', legs: [], createdAt: '' },
        { id: '2', ticker: 'QQQ', strategy: 'IC', expiryDate: '2026-01-17', legs: [], createdAt: '' },
        { id: '3', ticker: 'IWM', strategy: 'IC', expiryDate: '2026-01-17', legs: [], createdAt: '' },
      ]

      const wrapper = mount(OpenPositions, globalConfig)

      expect(wrapper.find('.position-count').text()).toBe('3 positions')
    })

    it('should use singular "position" for count of 1', async () => {
      mockPositions.value = [
        { id: '1', ticker: 'SPY', strategy: 'IC', expiryDate: '2026-01-17', legs: [], createdAt: '' },
      ]

      const wrapper = mount(OpenPositions, globalConfig)

      expect(wrapper.find('.position-count').text()).toBe('1 position')
    })
  })

  describe('Refresh Button', () => {
    it('should call refresh when header refresh button clicked', async () => {
      mockPositions.value = [
        { id: '1', ticker: 'SPY', strategy: 'IC', expiryDate: '2026-01-17', legs: [], createdAt: '' },
      ]

      const wrapper = mount(OpenPositions, globalConfig)
      const refreshBtn = wrapper.find('.header-actions .el-button')
      expect(refreshBtn.exists()).toBe(true)
      await refreshBtn.trigger('click')

      expect(mockRefresh).toHaveBeenCalled()
    })

    it('should show loading indicator during refresh', async () => {
      mockLoading.value = true
      mockPositions.value = [
        { id: '1', ticker: 'SPY', strategy: 'IC', expiryDate: '2026-01-17', legs: [], createdAt: '' },
      ]

      const wrapper = mount(OpenPositions, globalConfig)

      // The button should have loading prop - shows '...' in count
      expect(wrapper.find('.position-count').text()).toBe('...')
    })
  })
})
