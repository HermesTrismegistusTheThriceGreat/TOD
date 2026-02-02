<template>
  <header class="app-header">
    <div class="header-content">
      <div class="header-title">
        <h1>CASH-DASH</h1>
        <div class="header-subtitle-group">
          <div class="connection-status">
            <span
              class="status-indicator"
              :class="{ online: store.isConnected }"
            ></span>
            <span class="status-text">{{
              store.isConnected ? "Connected" : "Disconnected"
            }}</span>
          </div>
        </div>
      </div>
      <div class="header-right">
        <!-- <div class="header-stats">
          <div class="stat-item stat-pill">
            <span class="stat-label">Active:</span>
            <span class="stat-value">{{ headerBar.activeAgentCount }}</span>
          </div>
          <div class="stat-item stat-pill">
            <span class="stat-label">Running:</span>
            <span class="stat-value">{{ headerBar.runningAgentCount }}</span>
          </div>
          <div class="stat-item stat-pill">
            <span class="stat-label">Logs:</span>
            <span class="stat-value">{{ headerBar.logCount }}</span>
          </div>
          <div class="stat-item stat-pill">
            <span class="stat-label">WS Events:</span>
            <span class="stat-value">{{ headerBar.websocketEventCount }}</span>
          </div>
          <div class="stat-item stat-pill">
            <span class="stat-label">Cost:</span>
            <span class="stat-value">${{ headerBar.formattedCost }}</span>
          </div>
        </div> -->

        <div class="header-actions">
          <!-- Logs/ADWS view mode switcher - commented out per user request
          <div
            class="view-mode-switcher"
            title="Toggle view mode (Cmd+J / Ctrl+J)"
          >
            <button
              class="view-mode-btn"
              :class="{ active: store.viewMode === 'logs' }"
              @click="store.setViewMode('logs')"
            >
              LOGS
            </button>
            <button
              class="view-mode-btn"
              :class="{ active: store.viewMode === 'adws' }"
              @click="store.setViewMode('adws')"
            >
              ADWS
              <span v-if="store.runningAdws.length > 0" class="adw-badge">
                {{ store.runningAdws.length }}
              </span>
            </button>
            <span class="switcher-hint">(Cmd+J)</span>
          </div>
          -->
          <!-- Prompt button - commented out per user request
          <button
            class="btn-prompt"
            :class="{ active: store.commandInputVisible }"
            @click="store.toggleCommandInput"
            title="Toggle command input (Cmd+K / Ctrl+K)"
          >
            PROMPT <span class="btn-hint">(Cmd+K)</span>
          </button>
          -->
          <!-- Account Selector (desktop only, shows when authenticated) -->
          <AccountSelector v-if="authStore.isAuthenticated" class="desktop-nav" />
          <!-- Account Data Display (desktop only, shows when authenticated) -->
          <AccountDataDisplay v-if="authStore.isAuthenticated" class="desktop-nav" />
          <!-- Desktop navigation buttons (hidden on mobile) -->
          <button
            v-if="authStore.isAuthenticated"
            class="btn-prompt desktop-nav"
            :class="{ active: route.path === '/accounts' }"
            @click="router.push('/accounts')"
            title="Manage Accounts"
          >
            <svg class="settings-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
            </svg>
            ACCOUNTS
          </button>
          <button
            class="btn-prompt desktop-nav btn-alpaca"
            :class="{ active: isAlpacaAgentRoute }"
            @click="navigateToAlpacaAgent"
            title="Alpaca Trading Agent"
          >
            <svg class="alpaca-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
            ALPACA
          </button>
          <button
            class="btn-prompt desktop-nav"
            :class="{ active: store.viewMode === 'open-positions' && !isAlpacaAgentRoute }"
            @click="navigateToViewMode('open-positions')"
            title="View open positions"
          >
            POSITIONS
          </button>
          <button
            class="btn-prompt desktop-nav"
            :class="{ active: store.viewMode === 'calendar' && !isAlpacaAgentRoute }"
            @click="navigateToViewMode('calendar')"
            title="View calendar"
          >
            CALENDAR
          </button>
          <button
            class="btn-prompt desktop-nav"
            :class="{ active: store.viewMode === 'trade-stats' && !isAlpacaAgentRoute }"
            @click="navigateToViewMode('trade-stats')"
            title="View trade statistics"
          >
            TRADE STATS
          </button>
          <!-- Mobile hamburger menu -->
          <div class="mobile-menu">
            <button
              class="hamburger-btn"
              @click="toggleMobileMenu"
              :class="{ active: mobileMenuOpen }"
              title="Menu"
            >
              <span class="hamburger-icon">
                <span></span>
                <span></span>
                <span></span>
              </span>
            </button>
            <div v-if="mobileMenuOpen" class="mobile-dropdown">
              <!-- Account Selector in mobile menu -->
              <div v-if="authStore.isAuthenticated" class="mobile-account-selector">
                <AccountSelector />
              </div>
              <button
                v-if="authStore.isAuthenticated"
                class="mobile-menu-item"
                :class="{ active: route.path === '/accounts' }"
                @click="handleMobileNav('/accounts')"
              >
                MANAGE ACCOUNTS
              </button>
              <button
                class="mobile-menu-item"
                :class="{ active: isAlpacaAgentRoute }"
                @click="handleMobileAlpacaNav"
              >
                ALPACA AGENT
              </button>
              <button
                class="mobile-menu-item"
                :class="{ active: store.viewMode === 'open-positions' && !isAlpacaAgentRoute }"
                @click="handleMobileNav('open-positions')"
              >
                POSITIONS
              </button>
              <button
                class="mobile-menu-item"
                :class="{ active: store.viewMode === 'calendar' && !isAlpacaAgentRoute }"
                @click="handleMobileNav('calendar')"
              >
                CALENDAR
              </button>
              <button
                class="mobile-menu-item"
                :class="{ active: store.viewMode === 'trade-stats' && !isAlpacaAgentRoute }"
                @click="handleMobileNav('trade-stats')"
              >
                TRADE STATS
              </button>
              <button
                v-if="authStore.isAuthenticated"
                class="mobile-menu-item mobile-logout"
                @click="handleMobileLogout"
              >
                LOGOUT
              </button>
            </div>
          </div>
          <!-- Logout button - only show when authenticated (desktop only) -->
          <button
            v-if="authStore.isAuthenticated"
            class="btn-logout"
            @click="handleLogout"
            title="Sign out"
          >
            LOGOUT
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, watch, ref, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useHeaderBar } from "../composables/useHeaderBar";
import { useOrchestratorStore } from "../stores/orchestratorStore";
import { useAuthStore } from "../stores/authStore";
import { useAccountStore } from "../stores/accountStore";
import AccountSelector from "./AccountSelector.vue";
import AccountDataDisplay from "./AccountDataDisplay.vue";
import type { ViewMode } from "../types.d";

// Use header bar composable for state management
const headerBar = useHeaderBar();

// Use store for command input visibility
const store = useOrchestratorStore();

// Use auth store for authentication state
const authStore = useAuthStore();
const accountStore = useAccountStore();
const router = useRouter();
const route = useRoute();

// Mobile menu state
const mobileMenuOpen = ref(false);

// Alpaca Agent navigation
const isAlpacaAgentRoute = computed(() => route.path === '/alpaca-agent');

function navigateToAlpacaAgent() {
  if (route.path !== '/alpaca-agent') {
    router.push('/alpaca-agent');
  }
}

// Navigate to a view mode, ensuring we're on the home route first
function navigateToViewMode(mode: ViewMode) {
  if (route.path !== '/') {
    // Navigate to home first, then set view mode
    router.push('/').then(() => {
      store.setViewMode(mode);
    });
  } else {
    store.setViewMode(mode);
  }
}

function toggleMobileMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value;
}

function handleMobileNav(modeOrPath: ViewMode | string) {
  mobileMenuOpen.value = false;
  // If it's a route path (starts with /), navigate directly
  if (typeof modeOrPath === 'string' && modeOrPath.startsWith('/')) {
    router.push(modeOrPath);
  } else {
    // Otherwise treat it as a ViewMode
    navigateToViewMode(modeOrPath as ViewMode);
  }
}

function handleMobileAlpacaNav() {
  mobileMenuOpen.value = false;
  navigateToAlpacaAgent();
}

function handleMobileLogout() {
  mobileMenuOpen.value = false;
  handleLogout();
}

// Debug: Log auth state changes
watch(
  () => authStore.isAuthenticated,
  (newVal) => {
    console.log("[AppHeader] isAuthenticated changed:", newVal, "user:", authStore.user);
  },
  { immediate: true }
);

// Initialize account store only when authenticated
watch(
  () => authStore.isAuthenticated,
  async (isAuth) => {
    if (isAuth) {
      await accountStore.initialize();
    } else {
      // User logged out - reset store
      accountStore.reset();
    }
  },
  { immediate: true }
);

// Handle logout
async function handleLogout() {
  try {
    await authStore.signOut();

    // If already logged out, navigate immediately
    if (!authStore.isAuthenticated) {
      router.push("/login");
      return;
    }

    // Wait for auth state to update (race condition fix)
    // The reactive session from Better Auth updates asynchronously
    await new Promise<void>((resolve) => {
      const unwatch = watch(
        () => authStore.isAuthenticated,
        (isAuth) => {
          if (!isAuth) {
            unwatch();
            resolve();
          }
        },
        { immediate: true }
      );

      // Timeout after 2 seconds as safety measure
      setTimeout(() => {
        unwatch();
        resolve();
      }, 2000);
    });

    router.push("/login");
  } catch (error) {
    console.error("Logout failed:", error);
  }
}

// Toggle view mode with Cmd+J / Ctrl+J
function handleKeydown(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key === "j") {
    event.preventDefault();
    store.toggleViewMode();
  }
}

onMounted(() => {
  document.addEventListener("keydown", handleKeydown);
});

onUnmounted(() => {
  document.removeEventListener("keydown", handleKeydown);
});
</script>

<style scoped>
/* Header */
.app-header {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  padding: var(--spacing-md) var(--spacing-lg);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 100%;
}

.header-title {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.header-subtitle-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.header-title h1 {
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--text-primary);
  margin: 0;
}

.header-subtitle {
  font-size: 0.875rem;
  color: var(--accent-primary);
  font-weight: 600;
  letter-spacing: 0.025em;
}

/* View Mode Switcher */
.view-mode-switcher {
  display: flex;
  gap: 2px;
  background: var(--bg-tertiary);
  border-radius: 6px;
  padding: 2px;
  border: 1px solid var(--border-color);
}

.view-mode-btn {
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  border-radius: 4px;
  background: transparent;
  color: var(--text-muted);
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.view-mode-btn:hover {
  color: var(--text-primary);
  background: var(--bg-quaternary);
}

.view-mode-btn.active {
  background: var(--accent-primary);
  color: white;
  box-shadow: 0 0 8px rgba(6, 182, 212, 0.3);
}

.adw-badge {
  background: rgba(255, 255, 255, 0.2);
  padding: 0.125rem 0.375rem;
  border-radius: 8px;
  font-size: 0.65rem;
  font-weight: 700;
  min-width: 1rem;
  text-align: center;
}

.switcher-hint {
  font-size: 0.65rem;
  font-weight: 500;
  color: var(--text-secondary);
  opacity: 0.7;
  margin-left: 0rem;
  margin-right: 0.5rem;
  align-self: center;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: 0.75rem;
  color: var(--text-muted);
  padding-left: var(--spacing-md);
  border-left: 1px solid var(--border-color);
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}

.status-indicator.online {
  background: var(--status-success);
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
}

.status-text {
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-xl);
}

.header-stats {
  display: flex;
  gap: var(--spacing-xl);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding-left: var(--spacing-xl);
  border-left: 1px solid var(--border-color);
}

/* Account Selector in Header */
.header-actions > .account-selector {
  margin-right: var(--spacing-md);
  padding-right: var(--spacing-md);
  border-right: 1px solid var(--border-color);
}

.mobile-account-selector {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.mobile-account-selector .account-selector {
  width: 100%;
  max-width: 100%;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: 0.875rem;
}

.stat-label {
  color: var(--text-muted);
  font-weight: 500;
}

.stat-value {
  color: var(--text-primary);
  font-weight: 700;
  font-family: var(--font-mono);
}

/* Stat Pills - Flat Gray Badge Style */
.stat-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: 0.375rem 0.75rem;
  background: var(--bg-tertiary);
  border-radius: 12px;
  font-size: 0.875rem;
  border: 1px solid var(--border-light);
  transition: all 0.2s ease;
  white-space: nowrap;
}

.stat-pill:hover {
  background: var(--bg-quaternary);
  border-color: var(--border-color);
}

.stat-pill .stat-label {
  color: var(--text-muted);
  font-weight: 500;
  font-size: 0.8125rem;
}

.stat-pill .stat-value {
  color: var(--text-primary);
  font-weight: 700;
  font-family: var(--font-mono);
  font-size: 0.875rem;
}

/* Action Buttons */
.btn-prompt,
.btn-clear {
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.025em;
  border-radius: 4px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-hint {
  font-size: 0.65rem;
  font-weight: 500;
  opacity: 0.7;
  margin-left: 0.25rem;
}

.btn-prompt:hover,
.btn-clear:hover {
  background: var(--bg-quaternary);
  color: var(--text-primary);
  border-color: var(--accent-primary);
  transform: translateY(-1px);
}

.btn-prompt.active {
  background: var(--accent-primary);
  color: white;
  border-color: var(--accent-primary);
  box-shadow: 0 0 10px rgba(6, 182, 212, 0.3);
}

/* Alpaca Button */
.btn-alpaca {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.btn-alpaca .alpaca-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.btn-alpaca.active {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border-color: #3b82f6;
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.4);
}

.btn-alpaca:hover:not(.active) {
  border-color: #3b82f6;
  color: #3b82f6;
}

.btn-alpaca:hover:not(.active) .alpaca-icon {
  stroke: #3b82f6;
}

/* Settings Icon for Accounts Button */
.settings-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.btn-prompt .settings-icon {
  margin-right: 0.25rem;
}

/* Mobile Menu */
.mobile-menu {
  display: none;
  position: relative;
}

.hamburger-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  min-height: 44px;
  padding: 0;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.hamburger-btn:hover {
  background: var(--bg-quaternary);
  border-color: var(--accent-primary);
}

.hamburger-btn.active {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
}

.hamburger-icon {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 4px;
  width: 20px;
  height: 20px;
}

.hamburger-icon span {
  display: block;
  width: 18px;
  height: 2px;
  background: var(--text-secondary);
  border-radius: 1px;
  transition: all 0.2s ease;
}

.hamburger-btn:hover .hamburger-icon span,
.hamburger-btn.active .hamburger-icon span {
  background: var(--text-primary);
}

.hamburger-btn.active .hamburger-icon span {
  background: white;
}

.mobile-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 160px;
  max-width: calc(100vw - 2rem);
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 1000;
  overflow: hidden;
}

.mobile-menu-item {
  display: block;
  width: 100%;
  min-height: 44px;
  padding: 12px 16px;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.025em;
  text-align: left;
  background: transparent;
  color: var(--text-secondary);
  border: none;
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  transition: all 0.2s ease;
}

.mobile-menu-item:last-child {
  border-bottom: none;
}

.mobile-menu-item:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.mobile-menu-item.active {
  background: var(--accent-primary);
  color: white;
}

/* Mobile Logout Button */
.mobile-logout {
  color: var(--status-error, #ef4444);
  border-top: 1px solid var(--border-color);
  margin-top: 0.25rem;
}

.mobile-logout:hover {
  background: var(--status-error, #ef4444);
  color: white;
}

/* Responsive */
@media (max-width: 1200px) {
  .header-stats {
    gap: var(--spacing-md);
  }
}

@media (max-width: 1024px) {
  .header-title h1 {
    font-size: 0.875rem;
  }

  .header-subtitle {
    font-size: 0.75rem;
  }
}

/* Mobile responsive - show hamburger, hide desktop nav */
@media (max-width: 768px) {
  .desktop-nav {
    display: none;
  }

  .header-actions > .account-selector.desktop-nav {
    display: none;
  }

  .mobile-menu {
    display: block;
  }

  .header-content {
    padding: 0;
  }

  .header-actions {
    padding-left: var(--spacing-sm);
    border-left: none;
    gap: var(--spacing-xs);
  }

  .header-title h1 {
    font-size: 0.8rem;
  }

  .connection-status {
    display: none;
  }

  .btn-logout {
    display: none;
  }
}

/* Logout Button */
.btn-logout {
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.025em;
  border-radius: 4px;
  background: var(--bg-tertiary);
  color: var(--status-error, #ef4444);
  border: 1px solid var(--status-error, #ef4444);
  cursor: pointer;
  transition: all 0.2s ease;
  margin-left: var(--spacing-md);
}

.btn-logout:hover {
  background: var(--status-error, #ef4444);
  color: white;
  transform: translateY(-1px);
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.3);
}
</style>
