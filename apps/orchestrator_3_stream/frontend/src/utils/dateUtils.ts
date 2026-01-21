/**
 * Date Utilities for consistent date handling
 *
 * Solves the timezone offset bug when parsing ISO date strings (YYYY-MM-DD).
 * When JavaScript's new Date() parses "2026-01-21", it creates UTC midnight.
 * When displayed with toLocaleDateString() in US timezones (behind UTC),
 * the date shifts back one day showing "Jan 20, 2026" instead of "Jan 21, 2026".
 */

/**
 * Parse a YYYY-MM-DD date string as a LOCAL date (not UTC).
 * This prevents timezone offset issues when displaying dates.
 *
 * @param dateStr - ISO date string in YYYY-MM-DD format
 * @returns Date object representing the date in local timezone
 */
export function parseLocalDate(dateStr: string): Date {
  const [year, month, day] = dateStr.split('-').map(Number);
  return new Date(year, month - 1, day);
}

/**
 * Format a YYYY-MM-DD date string for display.
 * Uses local timezone interpretation to prevent date shift bugs.
 *
 * @param dateStr - ISO date string in YYYY-MM-DD format
 * @param options - Intl.DateTimeFormatOptions for formatting
 * @returns Formatted date string (e.g., "Jan 21, 2026")
 */
export function formatDateString(
  dateStr: string,
  options: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric', year: 'numeric' }
): string {
  if (!dateStr) return '';
  const date = parseLocalDate(dateStr);
  return date.toLocaleDateString('en-US', options);
}

/**
 * Calculate days between a YYYY-MM-DD date string and today.
 * Uses local timezone for both dates to ensure accurate day counting.
 *
 * @param dateStr - ISO date string in YYYY-MM-DD format
 * @returns Number of days until the target date (positive) or since (negative)
 */
export function daysUntil(dateStr: string): number {
  const target = parseLocalDate(dateStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffMs = target.getTime() - today.getTime();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}
