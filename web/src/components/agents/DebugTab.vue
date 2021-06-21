<template>
  <div v-if="!selectedAgent">No agent selected</div>
  <div v-else>
    <DebugLog :agentpk="selectedAgent" />
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

    return {
      // computed
      selectedAgent,
    };
  },
};
</script>