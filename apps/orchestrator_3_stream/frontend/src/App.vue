<template>
  <div class="app-container">
    <AppHeader />

    <main
      class="app-main"
      :class="{
        'sidebar-collapsed': isSidebarCollapsed,
        'chat-md': store.chatWidth === 'md',
        'chat-lg': store.chatWidth === 'lg',
        'no-sidebars': !shouldShowSidebars,
      }"
    >
      <AgentList
        v-if="shouldShowSidebars"
        class="app-sidebar left"
        :agents="store.agents"
        :selected-agent-id="store.selectedAgentId"
        @select-agent="handleSelectAgent"
        @add-agent="handleAddAgent"
        @collapse-change="handleSidebarCollapse"
      />

      <!-- Center Column: EventStream, AdwSwimlanes, or OpenPositions based on view mode -->
      <EventStream
        v-if="store.viewMode === 'logs'"
        ref="eventStreamRef"
        class="app-content center"
        :events="store.filteredEventStream"
        :current-filter="store.eventStreamFilter"
        :auto-scroll="true"
        @set-filter="handleSetFilter"
      />
      <AdwSwimlanes
        v-else-if="store.viewMode === 'adws'"
        class="app-content center"
      />
      <OpenPositions
        v-else-if="store.viewMode === 'open-positions'"
        class="app-content center"
      />
      <CalendarPage
        v-else-if="store.viewMode === 'calendar'"
        class="app-content center"
      />
      <TradeStatsGrid
        v-else-if="store.viewMode === 'trade-stats'"
        class="app-content center"
      />

      <OrchestratorChat
        v-if="shouldShowSidebars"
        class="app-sidebar right"
        :messages="store.chatMessages"
        :is-connected="store.isConnected"
        :is-typing="store.isTyping"
        :auto-scroll="store.autoScroll"
        @send="handleSendMessage"
      />
    </main>

    <!-- Global Command Input -->
    <GlobalCommandInput
      :visible="store.commandInputVisible"
      @send="handleSendMessage"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from "vue";
import AppHeader from "./components/AppHeader.vue";
import AgentList from "./components/AgentList.vue";
import EventStream from "./components/EventStream.vue";
import AdwSwimlanes from "./components/AdwSwimlanes.vue";
import OpenPositions from "./components/OpenPositions.vue";
import CalendarPage from "./components/CalendarPage.vue";
import TradeStatsGrid from "./components/TradeStatsGrid.vue";
import OrchestratorChat from "./components/OrchestratorChat.vue";
import GlobalCommandInput from "./components/GlobalCommandInput.vue";
import { useOrchestratorStore } from "./stores/orchestratorStore";
import { useKeyboardShortcuts } from "./composables/useKeyboardShortcuts";

// Use Pinia store
const store = useOrchestratorStore();

// Computed
const shouldShowSidebars = computed(() => {
  return store.viewMode === "logs" || store.viewMode === "adws";
});

// Initialize keyboard shortcuts
useKeyboardShortcuts();

// Component refs
const eventStreamRef = ref<InstanceType<typeof EventStream> | null>(null);

// Sidebar collapse state
const isSidebarCollapsed = ref(false);

// Initialize store on mount
onMounted(() => {
  store.initialize();
});

// Clean up on unmount to prevent duplicate connections during HMR
onUnmounted(() => {
  store.disconnectWebSocket();
});

// Handlers
const handleSelectAgent = (id: string) => {
  store.selectAgent(id);

  // Toggle agent filter in EventStream
  const agent = store.agents.find((a) => a.id === id);
  if (agent && eventStreamRef.value) {
    eventStreamRef.value.toggleAgentFilter(agent.name);
  }
};

const handleAddAgent = () => {
  console.log("Add agent clicked");
  // TODO: Open modal to create new agent
};

const handleSetFilter = (filter: string) => {
  store.setEventStreamFilter(filter as any);
};

const handleSendMessage = (message: string) => {
  store.sendUserMessage(message);
};

const handleSidebarCollapse = (isCollapsed: boolean) => {
  isSidebarCollapsed.value = isCollapsed;
};
</script>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Main Layout */
.app-main {
  flex: 1;
  display: grid;
  grid-template-columns: 280px 1fr 418px;
  overflow: hidden;
  transition: grid-template-columns 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Chat width variations */
.app-main.chat-md {
  grid-template-columns: 280px 1fr 518px;
}

.app-main.chat-lg {
  grid-template-columns: 280px 1fr 618px;
}

/* Combined with sidebar collapsed */
.app-main.sidebar-collapsed {
  grid-template-columns: 48px 1fr 418px;
}

.app-main.sidebar-collapsed.chat-md {
  grid-template-columns: 48px 1fr 518px;
}

.app-main.sidebar-collapsed.chat-lg {
  grid-template-columns: 48px 1fr 618px;
}

.app-main.no-sidebars {
  grid-template-columns: 1fr;
}

.app-sidebar,
.app-content {
  height: 100%;
  overflow: hidden;
}

/* Responsive */
@media (max-width: 1600px) {
  /* Limit large size on smaller screens */
  .app-main.chat-lg {
    grid-template-columns: 280px 1fr 518px; /* Fall back to medium */
  }

  .app-main.sidebar-collapsed.chat-lg {
    grid-template-columns: 48px 1fr 518px;
  }
}

@media (max-width: 1400px) {
  .app-main {
    grid-template-columns: 260px 1fr 385px;
  }

  .app-main.chat-md {
    grid-template-columns: 260px 1fr 450px; /* Reduced increase */
  }

  .app-main.chat-lg {
    grid-template-columns: 260px 1fr 450px; /* Cap at medium */
  }

  .app-main.sidebar-collapsed {
    grid-template-columns: 48px 1fr 385px;
  }

  .app-main.sidebar-collapsed.chat-md {
    grid-template-columns: 48px 1fr 450px;
  }

  .app-main.sidebar-collapsed.chat-lg {
    grid-template-columns: 48px 1fr 450px;
  }
}

@media (max-width: 1200px) {
  /* Force small size on narrow screens */
  .app-main,
  .app-main.chat-md,
  .app-main.chat-lg {
    grid-template-columns: 240px 1fr 352px;
  }

  .app-main.sidebar-collapsed,
  .app-main.sidebar-collapsed.chat-md,
  .app-main.sidebar-collapsed.chat-lg {
    grid-template-columns: 48px 1fr 352px;
  }
}

@media (max-width: 1024px) {
  .app-main,
  .app-main.chat-md,
  .app-main.chat-lg {
    grid-template-columns: 220px 1fr 330px;
  }

  .app-main.sidebar-collapsed,
  .app-main.sidebar-collapsed.chat-md,
  .app-main.sidebar-collapsed.chat-lg {
    grid-template-columns: 48px 1fr 330px;
  }
}

/* Mobile Responsive Design (< 768px) */
@media (max-width: 768px) {
  .app-container {
    height: auto !important;
    overflow-y: auto !important;
    -webkit-overflow-scrolling: touch;
  }

  /* Switch from Grid to Flex Column */
  .app-main,
  .app-main.chat-md,
  .app-main.chat-lg,
  .app-main.sidebar-collapsed,
  .app-main.sidebar-collapsed.chat-md,
  .app-main.sidebar-collapsed.chat-lg {
    display: flex !important;
    flex-direction: column;
    height: auto !important;
    overflow: visible !important;
  }

  /* Full width for all columns */
  .app-sidebar,
  .app-content {
    width: 100% !important;
    height: auto !important;
    min-width: 0 !important;
    overflow: visible !important;
    flex: none !important;
  }

  /* Content First */
  .app-content.center {
    order: 1;
    min-height: 50vh;
  }

  /* Chat Second */
  .app-sidebar.right {
    order: 2;
    height: 600px !important; /* Fixed height for chat area on mobile */
    border-top: 1px solid rgba(255, 255, 255, 0.1);
  }

  /* Agents Last (or hidden/collapsed) */
  .app-sidebar.left {
    order: 3;
    height: auto !important;
    display: flex;
    flex-direction: row;
    overflow-x: auto !important;
    padding: 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
  }
}
</style>
