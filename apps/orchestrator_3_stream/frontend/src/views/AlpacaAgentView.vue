<template>
  <div class="alpaca-agent-view">
    <AppHeader />
    <main class="alpaca-main">
      <AlpacaAgentChat />
    </main>
  </div>
</template>

<script setup lang="ts">
import AppHeader from "../components/AppHeader.vue";
import AlpacaAgentChat from "../components/AlpacaAgentChat.vue";
</script>

<style scoped>
.alpaca-agent-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-primary);
}

.alpaca-main {
  flex: 1;
  display: flex;
  overflow: hidden;
  padding: var(--spacing-lg);
}

@media (max-width: 768px) {
  .alpaca-main {
    padding: var(--spacing-sm);
  }
}
</style>
