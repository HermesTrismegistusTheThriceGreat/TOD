/**
 * Chat Service
 *
 * Handles HTTP and WebSocket communication for orchestrator chat
 */

import { apiClient } from './api'
import type { LoadChatRequest, LoadChatResponse, SendChatRequest, SendChatResponse } from '../types'
import { DEFAULT_CHAT_HISTORY_LIMIT } from '../config/constants'

// ============================================================================
// WebSocket Reconnection Configuration
// ============================================================================

const RECONNECT_CONFIG = {
  maxAttempts: 5,
  baseDelayMs: 1000,
  maxDelayMs: 30000,
}

let reconnectAttempts = 0
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
let isManualDisconnect = false
let isInitialConnection = true
let currentUrl: string = ''
let currentCallbacks: WebSocketCallbacks | null = null
let currentOnReconnect: (() => void) | null = null

// ============================================================================
// Alpaca Price Streaming Types
// ============================================================================

export interface OptionPriceUpdateMessage {
  type: 'option_price_update'
  update: {
    symbol: string
    bid_price: number
    ask_price: number
    mid_price: number
    last_price?: number
    volume: number
    timestamp: string
  }
  timestamp: string
}

export interface OptionPriceBatchMessage {
  type: 'option_price_batch'
  updates: Array<{
    symbol: string
    bid_price: number
    ask_price: number
    mid_price: number
    last_price?: number
    volume?: number
    timestamp?: string
  }>
  count: number
  timestamp: string
}

export interface PositionUpdateMessage {
  type: 'position_update'
  position: {
    symbol: string
    [key: string]: any  // Allow additional fields from OpenPosition
  }
  timestamp: string
}

export interface AlpacaStatusMessage {
  type: 'alpaca_status'
  status: 'connected' | 'disconnected' | 'error' | 'streaming_started' | 'streaming_stopped'
  details: Record<string, any>
  timestamp: string
}

export interface SpotPriceUpdateMessage {
  type: 'spot_price_update'
  update: {
    symbol: string
    bid_price: number
    ask_price: number
    mid_price: number
    last_price?: number
    timestamp: string
  }
  timestamp: string
}

/**
 * Get orchestrator agent information
 */
export async function getOrchestratorInfo() {
  const response = await apiClient.get('/get_orchestrator')
  return response.data
}

/**
 * Load chat history for orchestrator agent
 * Gets the most recent N messages from the database
 */
export async function loadChatHistory(
  orchestratorAgentId: string,
  limit: number = DEFAULT_CHAT_HISTORY_LIMIT
): Promise<LoadChatResponse> {
  const response = await apiClient.post<LoadChatResponse>('/load_chat', {
    orchestrator_agent_id: orchestratorAgentId,
    limit
  } as LoadChatRequest)

  return response.data
}

/**
 * Send message to orchestrator agent
 */
export async function sendMessage(
  message: string,
  orchestratorAgentId: string
): Promise<SendChatResponse> {
  const response = await apiClient.post<SendChatResponse>('/send_chat', {
    message,
    orchestrator_agent_id: orchestratorAgentId
  } as SendChatRequest)

  return response.data
}

/**
 * Reset orchestrator context to start a fresh conversation
 * Clears the session so next message starts with clean context
 * System prompt is always re-loaded, so no restart needed
 */
export async function resetContext(): Promise<{ status: string; message: string }> {
  const response = await apiClient.post('/reset_context')
  return response.data
}

/**
 * WebSocket connection callbacks
 */
export interface WebSocketCallbacks {
  /** Called for every WebSocket message received (before routing) */
  onMessageReceived?: () => void
  onChatStream: (chunk: string, isComplete: boolean) => void
  onTyping: (isTyping: boolean) => void
  onAgentLog?: (log: any) => void
  onOrchestratorChat?: (chat: any) => void
  onThinkingBlock?: (data: any) => void
  onToolUseBlock?: (data: any) => void
  onAgentCreated?: (agent: any) => void
  onAgentUpdated?: (data: any) => void
  onAgentDeleted?: (data: any) => void
  onAgentStatusChange?: (data: any) => void
  onAgentSummaryUpdate?: (data: any) => void
  onOrchestratorUpdated?: (data: any) => void
  onAutocompleteStarted?: (data: any) => void
  onAutocompleteCompleted?: (data: any) => void
  // ADW (AI Developer Workflow) events
  onAdwCreated?: (data: any) => void
  onAdwUpdated?: (data: any) => void
  onAdwEvent?: (data: any) => void
  onAdwStepChange?: (data: any) => void
  onAdwEventSummaryUpdate?: (data: any) => void
  // Alpaca price streaming events
  onOptionPriceUpdate?: (data: OptionPriceUpdateMessage) => void
  onOptionPriceBatch?: (data: OptionPriceBatchMessage) => void
  onPositionUpdate?: (data: PositionUpdateMessage) => void
  onAlpacaStatus?: (data: AlpacaStatusMessage) => void
  onSpotPriceUpdate?: (data: SpotPriceUpdateMessage) => void
  onError: (error: any) => void
  onConnected?: () => void
  onDisconnected?: () => void
}

/**
 * Connect to WebSocket for real-time updates
 */
export function connectWebSocket(
  url: string,
  callbacks: WebSocketCallbacks,
  onReconnect?: () => void
): WebSocket {
  // Store for reconnection
  currentUrl = url
  currentCallbacks = callbacks
  currentOnReconnect = onReconnect || null

  const ws = new WebSocket(url)

  ws.onopen = () => {
    // Reset reconnect attempts on successful connection
    reconnectAttempts = 0
    isManualDisconnect = false
    console.log('WebSocket connected')
    callbacks.onConnected?.()

    // Only call reconnection hook if this is NOT the initial connection
    if (onReconnect && !isInitialConnection) {
      console.log('WebSocket reconnected, triggering re-subscription')
      onReconnect()
    }

    isInitialConnection = false
  }

  ws.onmessage = (event) => {
    // Increment WebSocket event counter for ALL messages (before any processing)
    callbacks.onMessageReceived?.()

    try {
      const message = JSON.parse(event.data)

      // Route by message type
      switch (message.type) {
        case 'chat_stream':
          callbacks.onChatStream(
            message.chunk || '',
            message.is_complete || false
          )
          break

        case 'chat_typing':
          callbacks.onTyping(message.is_typing || false)
          break

        case 'agent_log':
          callbacks.onAgentLog?.(message)
          break

        case 'orchestrator_chat':
          callbacks.onOrchestratorChat?.(message)
          break

        case 'thinking_block':
          callbacks.onThinkingBlock?.(message)
          break

        case 'tool_use_block':
          callbacks.onToolUseBlock?.(message)
          break

        case 'agent_created':
          callbacks.onAgentCreated?.(message)
          break

        case 'agent_updated':
          callbacks.onAgentUpdated?.(message)
          break

        case 'agent_deleted':
          callbacks.onAgentDeleted?.(message)
          break

        case 'agent_status_changed':
          callbacks.onAgentStatusChange?.(message)
          break

        case 'agent_summary_update':
          callbacks.onAgentSummaryUpdate?.(message)
          break

        case 'orchestrator_updated':
          callbacks.onOrchestratorUpdated?.(message)
          break

        case 'autocomplete_started':
          callbacks.onAutocompleteStarted?.(message)
          break

        case 'autocomplete_completed':
          callbacks.onAutocompleteCompleted?.(message)
          break

        // ADW (AI Developer Workflow) events
        case 'adw_created':
          callbacks.onAdwCreated?.(message)
          break

        case 'adw_updated':
          callbacks.onAdwUpdated?.(message)
          break

        case 'adw_event':
          callbacks.onAdwEvent?.(message)
          break

        case 'adw_step_change':
          callbacks.onAdwStepChange?.(message)
          break

        case 'adw_event_summary_update':
          callbacks.onAdwEventSummaryUpdate?.(message)
          break

        // Alpaca price updates
        case 'option_price_update':
          callbacks.onOptionPriceUpdate?.(message as OptionPriceUpdateMessage)
          break

        case 'option_price_batch':
          callbacks.onOptionPriceBatch?.(message as OptionPriceBatchMessage)
          break

        case 'position_update':
          callbacks.onPositionUpdate?.(message as PositionUpdateMessage)
          break

        case 'alpaca_status':
          callbacks.onAlpacaStatus?.(message as AlpacaStatusMessage)
          break

        case 'spot_price_update':
          callbacks.onSpotPriceUpdate?.(message as SpotPriceUpdateMessage)
          break

        case 'error':
          callbacks.onError(message)
          break

        case 'connection_established':
          console.log('WebSocket connection established:', message.client_id)
          break

        default:
          console.log('Unknown message type:', message.type)
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error)
    }
  }

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
    callbacks.onError(error)
  }

  ws.onclose = () => {
    console.log('WebSocket disconnected')
    callbacks.onDisconnected?.()

    // Only attempt reconnection if not manually disconnected
    if (!isManualDisconnect && reconnectAttempts < RECONNECT_CONFIG.maxAttempts) {
      const delay = Math.min(
        RECONNECT_CONFIG.baseDelayMs * Math.pow(2, reconnectAttempts),
        RECONNECT_CONFIG.maxDelayMs
      )
      reconnectAttempts++
      console.log(`Attempting reconnection ${reconnectAttempts}/${RECONNECT_CONFIG.maxAttempts} in ${delay}ms`)

      reconnectTimeout = setTimeout(() => {
        if (currentUrl && currentCallbacks) {
          connectWebSocket(currentUrl, currentCallbacks, currentOnReconnect || undefined)
        }
      }, delay)
    } else if (reconnectAttempts >= RECONNECT_CONFIG.maxAttempts) {
      console.error('Max reconnection attempts reached')
    }
  }

  return ws
}

/**
 * Disconnect WebSocket
 */
export function disconnect(ws: WebSocket): void {
  isManualDisconnect = true
  isInitialConnection = true  // Reset so next manual connect is treated as initial
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout)
    reconnectTimeout = null
  }
  if (ws.readyState === WebSocket.OPEN) {
    ws.close()
  }
}
