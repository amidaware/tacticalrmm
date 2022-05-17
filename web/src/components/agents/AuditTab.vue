<template>
  <div v-if="!selectedAgent" class="q-pa-sm">No agent selected</div>
  <div v-else>
    <AuditManager :agent="selectedAgent" :tabHeight="tabHeight" />
  </div>
</template>

<script>
// composition imports
import { computed } from "vue";
import { useStore } from "vuex";

// ui imports
import AuditManager from "@/components/logs/AuditManager.vue";

export default {
  name: "AuditTab",
  components: {
    AuditManager,
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
