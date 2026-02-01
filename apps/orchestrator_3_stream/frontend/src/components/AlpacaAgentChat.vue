<template>
  <div class="alpaca-chat-container">
    <!-- Header -->
    <div class="chat-header">
      <div class="header-left">
        <div class="agent-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        </div>
        <div class="header-info">
          <h1>Alpaca Agent</h1>
          <span class="header-subtitle">Trading Account Management via Claude Code</span>
        </div>
      </div>
      <div class="header-right">
        <div class="status-badge" :class="connectionStatus">
          <span class="status-dot"></span>
          <span class="status-text">{{ statusText }}</span>
        </div>
        <button class="clear-btn" @click="clearHistory" title="Clear chat history">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Messages Area -->
    <div class="messages-area" ref="messagesRef">
      <!-- Welcome Message -->
      <div v-if="messages.length === 0" class="welcome-message">
        <div class="welcome-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        </div>
        <h2>Alpaca Trading Agent</h2>
        <p class="welcome-desc">
          Interact with your Alpaca trading account using natural language.
          This agent uses Claude Code to execute trading operations.
        </p>
        <div class="quick-commands">
          <h3>Quick Commands</h3>
          <div class="command-grid">
            <button class="command-chip" @click="sendQuickCommand('Check my account status and buying power')">
              Account Status
            </button>
            <button class="command-chip" @click="sendQuickCommand('Show all my open positions')">
              View Positions
            </button>
            <button class="command-chip" @click="sendQuickCommand('Get the current price of SPY')">
              SPY Price
            </button>
            <button class="command-chip" @click="sendQuickCommand('Show my recent orders')">
              Recent Orders
            </button>
          </div>
        </div>
        <div class="paper-trading-notice">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>Paper Trading Mode - No real money at risk</span>
        </div>
      </div>

      <!-- Chat Messages -->
      <div v-for="message in messages" :key="message.id" class="message" :class="message.role">
        <div class="message-header">
          <span class="message-role">{{ message.role === 'user' ? 'YOU' : 'ALPACA AGENT' }}</span>
          <span class="message-time">{{ formatTime(message.timestamp) }}</span>
        </div>
        <div class="message-content">
          <!-- User message -->
          <div v-if="message.role === 'user'" class="user-content">
            {{ message.content }}
          </div>

          <!-- Assistant message with streaming support -->
          <div v-else class="assistant-content">
            <!-- Thinking indicator -->
            <div v-if="message.isThinking" class="thinking-block">
              <div class="thinking-header">
                <svg class="thinking-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 6v6l4 2" />
                </svg>
                <span>Processing...</span>
              </div>
              <div v-if="message.thinkingContent" class="thinking-content">
                {{ message.thinkingContent }}
              </div>
            </div>

            <!-- Tool use indicator -->
            <div v-if="message.toolUse" class="tool-use-block">
              <div class="tool-header">
                <svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" />
                </svg>
                <span>{{ message.toolUse.name }}</span>
              </div>
              <div v-if="message.toolUse.input" class="tool-input">
                <pre>{{ formatToolInput(message.toolUse.input) }}</pre>
              </div>
            </div>

            <!-- Main response content -->
            <div v-if="message.content" class="response-content" v-html="renderMarkdown(message.content)"></div>

            <!-- Streaming cursor -->
            <span v-if="message.isStreaming" class="streaming-cursor"></span>
          </div>
        </div>
      </div>

      <!-- Loading indicator -->
      <div v-if="isLoading && !currentStreamingMessage" class="loading-indicator">
        <div class="loading-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <span class="loading-text">Connecting to Alpaca agent...</span>
      </div>

      <div ref="bottomAnchor"></div>
    </div>

    <!-- Input Area -->
    <div class="input-area">
      <!-- Warning when no credential selected -->
      <div v-if="!accountStore.activeCredentialId" class="no-credential-warning">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span>Select a trading account to start chatting</span>
      </div>
      <div class="input-wrapper">
        <textarea
          ref="inputRef"
          v-model="userInput"
          @keydown="handleKeydown"
          placeholder="Ask about your account, positions, or place orders..."
          :disabled="isLoading"
          rows="1"
        ></textarea>
        <button
          class="send-btn"
          @click="sendMessage"
          :disabled="!userInput.trim() || isLoading || !accountStore.activeCredentialId"
          title="Send message (Enter)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 2L11 13" />
            <path d="M22 2l-7 20-4-9-9-4 20-7z" />
          </svg>
        </button>
      </div>
      <div class="input-hints">
        <span class="hint">Press <kbd>Enter</kbd> to send, <kbd>Shift+Enter</kbd> for new line</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { renderMarkdown } from '../utils/markdown'
import { useAccountStore } from '@/stores/accountStore'

// Get API base URL from environment
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:9403'

// Initialize account store for credential context
const accountStore = useAccountStore()

// Types
interface ToolUse {
  name: string
  input: Record<string, any> | string
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  isStreaming?: boolean
  isThinking?: boolean
  thinkingContent?: string
  toolUse?: ToolUse
}

// State
const messages = ref<ChatMessage[]>([])
const userInput = ref('')
const isLoading = ref(false)
const connectionStatus = ref<'ready' | 'loading' | 'error'>('ready')
const currentStreamingMessage = ref<ChatMessage | null>(null)

// Refs
const messagesRef = ref<HTMLElement | null>(null)
const bottomAnchor = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)

// WebSocket for streaming (if backend supports it)
let ws: WebSocket | null = null

// Computed
const statusText = computed(() => {
  switch (connectionStatus.value) {
    case 'loading': return 'Processing...'
    case 'error': return 'Error'
    default: return 'Ready'
  }
})

// Methods
function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatToolInput(input: Record<string, any> | string): string {
  if (typeof input === 'string') return input
  return JSON.stringify(input, null, 2)
}

async function scrollToBottom() {
  await nextTick()
  bottomAnchor.value?.scrollIntoView({ behavior: 'smooth' })
}

function sendQuickCommand(command: string) {
  userInput.value = command
  sendMessage()
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

async function sendMessage() {
  const content = userInput.value.trim()
  if (!content || isLoading.value) return

  // Guard: Require active credential for chat
  if (!accountStore.activeCredentialId) {
    connectionStatus.value = 'error'
    // Add error message to chat
    const errorMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: 'Please select a trading account before sending messages. Use the account selector in the header.',
      timestamp: new Date()
    }
    messages.value.push(errorMessage)
    scrollToBottom()
    // Reset status after showing error
    setTimeout(() => {
      connectionStatus.value = 'ready'
    }, 3000)
    return
  }

  // Add user message
  const userMessage: ChatMessage = {
    id: crypto.randomUUID(),
    role: 'user',
    content,
    timestamp: new Date()
  }
  messages.value.push(userMessage)
  userInput.value = ''

  // Reset textarea height
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
  }

  isLoading.value = true
  connectionStatus.value = 'loading'
  scrollToBottom()

  try {
    // Create a streaming assistant message
    const assistantMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
      isThinking: true
    }
    messages.value.push(assistantMessage)
    currentStreamingMessage.value = assistantMessage
    scrollToBottom()

    // Call the backend API to invoke alpaca-mcp agent with credential_id
    const response = await fetch(`${API_BASE_URL}/api/alpaca-agent/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: content,
        credential_id: accountStore.activeCredentialId
      })
    })

    if (!response.ok) {
      // Handle 403 specifically - may indicate stale credential
      if (response.status === 403) {
        // Clear stale credential from store and localStorage
        accountStore.activeCredentialId = null
        try {
          localStorage.removeItem('activeCredentialId')
        } catch (e) {
          console.warn('Failed to clear localStorage:', e)
        }
        throw new Error('Credential no longer valid. Please select a trading account.')
      }

      // Try to extract error message from response body
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`
      try {
        const errorData = await response.json()
        if (errorData.error) {
          errorMessage = errorData.error
        } else if (errorData.message) {
          errorMessage = errorData.message
        }
      } catch {
        // Response wasn't JSON, use default error message
      }
      throw new Error(errorMessage)
    }

    // Check if response is streaming
    if (response.headers.get('content-type')?.includes('text/event-stream')) {
      // Handle SSE streaming
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') continue

              try {
                const parsed = JSON.parse(data)
                handleStreamChunk(parsed, assistantMessage)
              } catch {
                // Plain text chunk
                assistantMessage.content += data
                assistantMessage.isThinking = false
              }
              scrollToBottom()
            }
          }
        }
      }
    } else {
      // Handle regular JSON response
      const data = await response.json()
      assistantMessage.content = data.response || data.message || JSON.stringify(data)
      assistantMessage.isThinking = false
    }

    // Mark streaming complete
    assistantMessage.isStreaming = false
    currentStreamingMessage.value = null
    connectionStatus.value = 'ready'

  } catch (error) {
    console.error('Failed to send message:', error)
    connectionStatus.value = 'error'

    // Update the streaming message with error
    if (currentStreamingMessage.value) {
      currentStreamingMessage.value.isStreaming = false
      currentStreamingMessage.value.isThinking = false
      currentStreamingMessage.value.content = `Error: ${error instanceof Error ? error.message : 'Failed to communicate with Alpaca agent'}`
    }

    // Reset after showing error
    setTimeout(() => {
      connectionStatus.value = 'ready'
    }, 3000)
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}

function handleStreamChunk(data: any, message: ChatMessage) {
  // Handle different types of stream events
  if (data.type === 'thinking') {
    message.isThinking = true
    message.thinkingContent = data.content
  } else if (data.type === 'tool_use') {
    message.toolUse = {
      name: data.tool_name || data.name,
      input: data.tool_input || data.input
    }
    message.isThinking = false
  } else if (data.type === 'text' || data.type === 'content') {
    message.content += data.content || data.text || ''
    message.isThinking = false
  } else if (data.content) {
    message.content += data.content
    message.isThinking = false
  }
}

function clearHistory() {
  messages.value = []
  currentStreamingMessage.value = null
}

// Auto-resize textarea
function autoResizeTextarea() {
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
    inputRef.value.style.height = Math.min(inputRef.value.scrollHeight, 150) + 'px'
  }
}

// Lifecycle
onMounted(() => {
  // Focus input on mount
  inputRef.value?.focus()

  // Watch for input changes to auto-resize
  if (inputRef.value) {
    inputRef.value.addEventListener('input', autoResizeTextarea)
  }
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>

<style scoped>
.alpaca-chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
}

/* Header */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid var(--border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.agent-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border-radius: 10px;
  color: white;
}

.agent-icon svg {
  width: 24px;
  height: 24px;
}

.header-info h1 {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.header-subtitle {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-badge.ready {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.3);
  color: rgb(16, 185, 129);
}

.status-badge.loading {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.3);
  color: rgb(59, 130, 246);
}

.status-badge.error {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
  color: rgb(239, 68, 68);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.status-badge.loading .status-dot {
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.clear-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;
}

.clear-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.5);
  color: rgb(239, 68, 68);
}

.clear-btn svg {
  width: 18px;
  height: 18px;
}

/* Messages Area */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

/* Welcome Message */
.welcome-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--spacing-xl);
  flex: 1;
}

.welcome-icon {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border-radius: 20px;
  color: white;
  margin-bottom: var(--spacing-lg);
}

.welcome-icon svg {
  width: 48px;
  height: 48px;
}

.welcome-message h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-sm);
}

.welcome-desc {
  color: var(--text-muted);
  max-width: 400px;
  margin-bottom: var(--spacing-lg);
  line-height: 1.5;
}

.quick-commands {
  width: 100%;
  max-width: 500px;
}

.quick-commands h3 {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: var(--spacing-md);
}

.command-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-sm);
}

.command-chip {
  padding: 10px 16px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 8px;
  color: rgb(59, 130, 246);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.command-chip:hover {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.5);
  transform: translateY(-1px);
}

.paper-trading-notice {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-xl);
  padding: 10px 16px;
  background: rgba(234, 179, 8, 0.1);
  border: 1px solid rgba(234, 179, 8, 0.3);
  border-radius: 8px;
  color: rgb(234, 179, 8);
  font-size: 0.8125rem;
}

.paper-trading-notice svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

/* Messages */
.message {
  display: flex;
  flex-direction: column;
  max-width: 85%;
}

.message.user {
  align-self: flex-end;
}

.message.assistant {
  align-self: flex-start;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  gap: var(--spacing-md);
}

.message-role {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.message-time {
  font-size: 0.7rem;
  color: var(--text-dim);
}

.message-content {
  padding: var(--spacing-md);
  border-radius: 12px;
  font-size: 0.875rem;
  line-height: 1.6;
}

.message.user .message-content {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-content {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  border-bottom-left-radius: 4px;
}

/* Thinking Block */
.thinking-block {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: rgba(139, 92, 246, 0.1);
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: 8px;
  margin-bottom: var(--spacing-sm);
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: rgb(139, 92, 246);
  font-size: 0.8125rem;
  font-weight: 600;
}

.thinking-icon {
  width: 16px;
  height: 16px;
  animation: spin 2s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.thinking-content {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-style: italic;
}

/* Tool Use Block */
.tool-use-block {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 8px;
  margin-bottom: var(--spacing-sm);
}

.tool-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: rgb(16, 185, 129);
  font-size: 0.8125rem;
  font-weight: 600;
}

.tool-icon {
  width: 16px;
  height: 16px;
}

.tool-input {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  padding: var(--spacing-sm);
  overflow-x: auto;
}

.tool-input pre {
  margin: 0;
  font-size: 0.75rem;
  font-family: 'JetBrains Mono', monospace;
  color: var(--text-secondary);
}

/* Response Content (Markdown) */
.response-content {
  line-height: 1.6;
}

.response-content :deep(p) {
  margin: 0 0 0.75em;
}

.response-content :deep(p:last-child) {
  margin-bottom: 0;
}

/* Headers */
.response-content :deep(h1),
.response-content :deep(h2),
.response-content :deep(h3),
.response-content :deep(h4),
.response-content :deep(h5),
.response-content :deep(h6) {
  margin: 1em 0 0.5em;
  font-weight: 700;
  line-height: 1.3;
  color: var(--text-primary);
}

.response-content :deep(h1:first-child),
.response-content :deep(h2:first-child),
.response-content :deep(h3:first-child),
.response-content :deep(h4:first-child),
.response-content :deep(h5:first-child),
.response-content :deep(h6:first-child) {
  margin-top: 0;
}

.response-content :deep(h1) {
  font-size: 1.5em;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.3em;
}

.response-content :deep(h2) {
  font-size: 1.3em;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.3em;
}

.response-content :deep(h3) {
  font-size: 1.15em;
  color: rgb(16, 185, 129);
}

.response-content :deep(h4) {
  font-size: 1.05em;
}

.response-content :deep(h5) {
  font-size: 1em;
}

.response-content :deep(h6) {
  font-size: 0.9em;
  color: var(--text-secondary);
}

/* Lists */
.response-content :deep(ul),
.response-content :deep(ol) {
  margin: 0.5em 0 0.75em;
  padding-left: 1.5em;
}

.response-content :deep(ul) {
  list-style-type: disc;
}

.response-content :deep(ol) {
  list-style-type: decimal;
}

.response-content :deep(li) {
  margin: 0.25em 0;
  line-height: 1.5;
}

.response-content :deep(li p) {
  margin: 0.25em 0;
}

.response-content :deep(li > ul),
.response-content :deep(li > ol) {
  margin: 0.25em 0;
}

/* Blockquotes */
.response-content :deep(blockquote) {
  margin: 0.75em 0;
  padding: 0.5em 1em;
  border-left: 3px solid rgb(59, 130, 246);
  background: rgba(59, 130, 246, 0.1);
  border-radius: 0 8px 8px 0;
}

.response-content :deep(blockquote p) {
  margin: 0;
}

/* Horizontal rule */
.response-content :deep(hr) {
  margin: 1em 0;
  border: none;
  border-top: 1px solid var(--border-color);
}

/* Links */
.response-content :deep(a) {
  color: rgb(59, 130, 246);
  text-decoration: none;
}

.response-content :deep(a:hover) {
  text-decoration: underline;
}

/* Code */
.response-content :deep(code) {
  background: rgba(0, 0, 0, 0.3);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85em;
}

.response-content :deep(pre) {
  background: rgba(0, 0, 0, 0.3);
  padding: var(--spacing-md);
  border-radius: 8px;
  overflow-x: auto;
  margin: var(--spacing-sm) 0;
}

.response-content :deep(pre code) {
  background: none;
  padding: 0;
}

/* Tables */
.response-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: var(--spacing-sm) 0;
  font-size: 0.85em;
}

.response-content :deep(th),
.response-content :deep(td) {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  text-align: left;
}

.response-content :deep(th) {
  background: rgba(0, 0, 0, 0.2);
  font-weight: 600;
}

/* Text formatting */
.response-content :deep(strong) {
  font-weight: 700;
  color: var(--accent-primary);
}

.response-content :deep(em) {
  font-style: italic;
}

.response-content :deep(del) {
  text-decoration: line-through;
  opacity: 0.7;
}

/* Streaming Cursor */
.streaming-cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background: var(--accent-primary);
  margin-left: 2px;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* Loading Indicator */
.loading-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  align-self: flex-start;
}

.loading-dots {
  display: flex;
  gap: 4px;
}

.loading-dots span {
  width: 8px;
  height: 8px;
  background: var(--accent-primary);
  border-radius: 50%;
  animation: loadingDot 1.4s infinite;
}

.loading-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.loading-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes loadingDot {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.loading-text {
  font-size: 0.8125rem;
  color: var(--text-muted);
}

/* Input Area */
.input-area {
  padding: var(--spacing-md) var(--spacing-lg);
  background: rgba(0, 0, 0, 0.2);
  border-top: 1px solid var(--border-color);
}

.input-wrapper {
  display: flex;
  gap: var(--spacing-sm);
  align-items: flex-end;
}

.input-wrapper textarea {
  flex: 1;
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  color: var(--text-primary);
  font-size: 0.9rem;
  font-family: inherit;
  resize: none;
  min-height: 44px;
  max-height: 150px;
  line-height: 1.5;
  transition: border-color 0.2s;
}

.input-wrapper textarea:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.input-wrapper textarea::placeholder {
  color: var(--text-muted);
}

.input-wrapper textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border: none;
  border-radius: 12px;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-btn svg {
  width: 20px;
  height: 20px;
}

.input-hints {
  margin-top: var(--spacing-xs);
  text-align: center;
}

.hint {
  font-size: 0.7rem;
  color: var(--text-dim);
}

.hint kbd {
  display: inline-block;
  padding: 2px 6px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-family: inherit;
  font-size: 0.65rem;
}

/* No Credential Warning */
.no-credential-warning {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 10px 16px;
  background: rgba(234, 179, 8, 0.1);
  border: 1px solid rgba(234, 179, 8, 0.3);
  border-radius: 8px;
  color: rgb(234, 179, 8);
  font-size: 0.8125rem;
  margin-bottom: var(--spacing-sm);
}

.no-credential-warning svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .chat-header {
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .header-info h1 {
    font-size: 1rem;
  }

  .header-subtitle {
    display: none;
  }

  .messages-area {
    padding: var(--spacing-md);
  }

  .message {
    max-width: 95%;
  }

  .command-grid {
    grid-template-columns: 1fr;
  }

  .input-area {
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .input-hints {
    display: none;
  }
}
</style>
