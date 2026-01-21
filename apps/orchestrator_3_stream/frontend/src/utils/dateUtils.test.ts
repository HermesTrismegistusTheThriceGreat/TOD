import { describe, it, expect } from 'vitest'
import { parseLocalDate, formatDateString, daysUntil } from './dateUtils'

describe('dateUtils', () => {
  describe('parseLocalDate', () => {
    it('should parse YYYY-MM-DD as local date', () => {
      const date = parseLocalDate('2026-01-21')
      expect(date.getFullYear()).toBe(2026)
      expect(date.getMonth()).toBe(0) // January is 0
      expect(date.getDate()).toBe(21)
    })

    it('should not shift date due to timezone', () => {
      // This is the key test - ensure "2026-01-21" stays as Jan 21
      const date = parseLocalDate('2026-01-21')
      const formatted = date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      })
      expect(formatted).toBe('Jan 21, 2026')
    })
  })

  describe('formatDateString', () => {
    it('should format date correctly without timezone shift', () => {
      const formatted = formatDateString('2026-01-21')
      expect(formatted).toBe('Jan 21, 2026')
    })

    it('should handle custom options', () => {
      const formatted = formatDateString('2026-01-21', {
        month: 'short',
        day: 'numeric'
      })
      expect(formatted).toBe('Jan 21')
    })

    it('should return empty string for empty input', () => {
      const formatted = formatDateString('')
      expect(formatted).toBe('')
    })

    it('should not shift GLD symbol expiration date', () => {
      // GLD260121... should display as Jan 21, 2026
      const formatted = formatDateString('2026-01-21')
      expect(formatted).toContain('21')
      expect(formatted).toContain('2026')
    })
  })

  describe('daysUntil', () => {
    it('should calculate days until future date', () => {
      const today = new Date()
      const tomorrow = new Date(today)
      tomorrow.setDate(tomorrow.getDate() + 1)

      const dateStr = `${tomorrow.getFullYear()}-${String(tomorrow.getMonth() + 1).padStart(2, '0')}-${String(tomorrow.getDate()).padStart(2, '0')}`
      const days = daysUntil(dateStr)

      expect(days).toBe(1)
    })

    it('should return positive value for future dates', () => {
      const days = daysUntil('2030-01-01')
      expect(days).toBeGreaterThan(0)
    })

    it('should return negative value for past dates', () => {
      const days = daysUntil('2020-01-01')
      expect(days).toBeLessThan(0)
    })
  })
})
