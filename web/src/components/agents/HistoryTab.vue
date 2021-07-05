<template>
  <div v-if="!selectedAgent">No agent selected</div>
  <div v-else></div>
</template>

<script>
// composition imports
import { computed } from "vue";
import { useStore } from "vuex";

export default {
  name: "HistoryTab",
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