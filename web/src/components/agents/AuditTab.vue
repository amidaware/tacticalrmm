<template>
  <div v-if="!selectedAgent">No agent selected</div>
  <div v-else>
    <AuditManager :agentpk="selectedAgent" />
  </div>
</template>

<script>
// composition imports
import { computed } from "vue";
import { useStore } from "vuex";

// ui imports
import AuditManager from "@/components/logs/AuditManager";

export default {
  name: "AuditTab",
  components: {
    AuditManager,
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