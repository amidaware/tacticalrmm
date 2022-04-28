<template>
  <q-page>
    <SummaryTab />
    <q-separator />
    <SubTableTabs
      :style="{ height: `${tabHeight + 38}px` }"
      :activeTabs="[
        'checks',
        'tasks',
        'patches',
        'software',
        'history',
        'notes',
        'assets',
        'audit',
      ]"
    />
  </q-page>
</template>

<script>
// composition imports
import { ref } from "vue";
import { useStore } from "vuex";
import { useRoute } from "vue-router";
import { useQuasar } from "quasar";

// ui imports
import SummaryTab from "@/components/agents/SummaryTab";
import SubTableTabs from "@/components/SubTableTabs";

export default {
  name: "AgentView",
  components: {
    SummaryTab,
    SubTableTabs,
  },
  provide() {
    return {
      // eslint-disable-next-line @typescript-eslint/no-empty-function
      refreshDashboard: () => {}, // noop
    };
  },
  setup() {
    const store = useStore();
    const route = useRoute();
    const $q = useQuasar();

    const tabHeight = ref($q.screen.height - 309 - 50 - 36);

    store.commit("setActiveRow", route.params.agent_id);
    store.state.tabHeight = `${tabHeight.value}px`;

    return {
      tabHeight,
    };
  },
};
</script>
