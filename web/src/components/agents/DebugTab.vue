<template>
  <div v-if="!selectedAgent" class="q-pa-sm">No agent selected</div>
  <div v-else>
    <DebugLog :agent="selectedAgent" :tabHeight="tabHeight" />
  </div>
</template>

<script>
// composition imports
import { computed } from "vue";
import { useStore } from "vuex";

// ui imports
import DebugLog from "@/components/logs/DebugLog";

export default {
  name: "DebugTab",
  components: {
    DebugLog,
  },
  setup() {
    const store = useStore();
    const selectedAgent = computed(() => store.state.selectedRow);
    const tabHeight = computed(() => store.state.tabHeight);

    return {
      // computed
      selectedAgent,
      tabHeight,
    };
  },
};
</script>
