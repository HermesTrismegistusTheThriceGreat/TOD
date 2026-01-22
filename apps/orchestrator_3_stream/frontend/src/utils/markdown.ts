/**
 * Markdown Rendering Utility
 *
 * Provides secure markdown-to-HTML conversion with syntax highlighting.
 * Uses marked for markdown parsing, DOMPurify for XSS protection,
 * and highlight.js for code block syntax highlighting.
 */

import { marked } from 'marked'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js'

// Configure marked for optimal rendering
marked.setOptions({
  // Enable syntax highlighting for code blocks
  highlight: function(code: string, lang: string) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value
      } catch (err) {
        console.error('Syntax highlighting error:', err)
      }
    }
    // Auto-detect language if not specified
    return hljs.highlightAuto(code).value
  },

  // GitHub Flavored Markdown
  gfm: true,

  // Convert \n to <br> for better line breaks
  breaks: true,

  // Use pedantic mode for more strict markdown parsing
  pedantic: false,

  // Enable smartypants for better typography
  smartypants: true,
})

/**
 * Preprocess text to improve markdown rendering of Claude Code output.
 *
 * Claude Code often outputs text in a continuous format optimized for terminals,
 * where list items and sections run together. This function normalizes the text
 * to help the markdown parser recognize these elements.
 *
 * @param text - Raw text from Claude Code
 * @returns Preprocessed text with proper newlines for markdown
 */
function preprocessClaudeOutput(text: string): string {
  let result = text

  // Insert newline before markdown headers (### Header) that aren't at line start
  // Matches: "text### Header" -> "text\n\n### Header"
  result = result.replace(/([^\n])(#{1,6}\s)/g, '$1\n\n$2')

  // Insert newline before unordered list items that appear after non-whitespace
  // Matches: "text- item" -> "text\n- item" (but not "text - item" which is likely a dash in text)
  // Only match when "-" is followed by a space and word character (real list items)
  result = result.replace(/([^\n\s])(-\s+\w)/g, '$1\n$2')

  // Handle ":-" pattern (colon followed by dash) which often indicates a list start
  // Matches: "is:- Bid" -> "is:\n- Bid"
  result = result.replace(/:(-\s+)/g, ':\n$1')

  // Insert newline before numbered list items (1. 2. 3. etc.)
  // Matches: "text1. item" -> "text\n1. item"
  result = result.replace(/([^\n\d])(\d+\.\s+\w)/g, '$1\n$2')

  // Insert newline before bold section headers like "**Header:**" or "**Header**:"
  // These often start new sections in Claude output
  result = result.replace(/([^\n])(\*\*[A-Z][^*]+\*\*:?)/g, '$1\n\n$2')

  // Insert newline before sentences that start with "Your" after a value (common Claude pattern)
  // Matches: "$100.00Your account" -> "$100.00\n\nYour account"
  result = result.replace(/([\d.]+)(Your\s)/g, '$1\n\n$2')

  // Insert newline before sentences that follow a period and start with capital letter
  // But avoid breaking normal sentence flow - only when there's a number or symbol before
  result = result.replace(/(\d)(\.)((?:Your|The|This|It|All|No)\s)/g, '$1$2\n\n$3')

  // Normalize multiple newlines to maximum of 2 (paragraph break)
  result = result.replace(/\n{3,}/g, '\n\n')

  return result
}

/**
 * Render markdown to sanitized HTML
 *
 * @param markdown - Raw markdown string
 * @returns Sanitized HTML string safe for v-html
 *
 * @example
 * ```typescript
 * const html = renderMarkdown('# Hello\n\nThis is **bold**')
 * // Returns: '<h1>Hello</h1><p>This is <strong>bold</strong></p>'
 * ```
 */
export function renderMarkdown(markdown: string): string {
  if (!markdown) return ''

  try {
    // Preprocess to fix Claude Code's continuous output format
    const preprocessed = preprocessClaudeOutput(markdown)

    // Parse markdown to HTML
    const rawHtml = marked.parse(preprocessed, { async: false }) as string

    // Sanitize HTML to prevent XSS attacks
    const sanitizedHtml = DOMPurify.sanitize(rawHtml, {
      // Allow these additional tags
      ADD_TAGS: ['iframe'],

      // Allow these additional attributes
      ADD_ATTR: ['target', 'rel', 'class'],

      // Allow data attributes (for code blocks)
      ALLOW_DATA_ATTR: true,
    })

    return sanitizedHtml
  } catch (error) {
    console.error('Markdown rendering error:', error)
    // Fallback: return escaped text
    return DOMPurify.sanitize(markdown)
  }
}

/**
 * Render inline markdown (no block elements)
 * Useful for single-line markdown in constrained spaces
 *
 * @param markdown - Raw markdown string
 * @returns Sanitized HTML string with only inline elements
 */
export function renderInlineMarkdown(markdown: string): string {
  if (!markdown) return ''

  try {
    const rawHtml = marked.parseInline(markdown) as string
    return DOMPurify.sanitize(rawHtml, {
      ALLOWED_TAGS: ['strong', 'em', 'code', 'a', 'del', 'ins'],
      ALLOWED_ATTR: ['href', 'title', 'target', 'rel'],
    })
  } catch (error) {
    console.error('Inline markdown rendering error:', error)
    return DOMPurify.sanitize(markdown)
  }
}

/**
 * Check if a string contains markdown formatting
 * Useful for conditional rendering
 *
 * @param text - Text to check
 * @returns True if text appears to contain markdown
 */
export function hasMarkdown(text: string): boolean {
  if (!text) return false

  // Check for common markdown patterns
  const markdownPatterns = [
    /#{1,6}\s/,           // Headers
    /\*\*.*?\*\*/,        // Bold
    /\*.*?\*/,            // Italic
    /__.*?__/,            // Bold (alternative)
    /_.*?_/,              // Italic (alternative)
    /`.*?`/,              // Inline code
    /```[\s\S]*?```/,     // Code blocks
    /^\s*[-*+]\s/m,       // Unordered lists
    /^\s*\d+\.\s/m,       // Ordered lists
    /\[.*?\]\(.*?\)/,     // Links
    /!\[.*?\]\(.*?\)/,    // Images
  ]

  return markdownPatterns.some(pattern => pattern.test(text))
}
