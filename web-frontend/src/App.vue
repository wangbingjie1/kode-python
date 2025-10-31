<template>
  <div id="app" class="h-screen">
    <RouterView />
    <NotificationContainer />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import NotificationContainer from '@/components/NotificationContainer.vue'
</script>

<style scoped>
#app {
  height: 100vh;
  overflow: hidden;
}
</style>
