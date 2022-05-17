<template>
  <div>
    <q-tabs
      v-model="tab"
      dense
      inline-label
      class="text-grey"
      active-color="primary"
      indicator-color="primary"
      align="left"
      narrow-indicator
    >
      <q-tab name="terminal" icon="fas fa-terminal" label="Terminal" />
      <q-tab
        name="filebrowser"
        icon="far fa-folder-open"
        label="File Browser"
      />
      <q-tab
        v-if="$route.query.agentPlatform === 'windows'"
        name="services"
        icon="fas fa-cogs"
        label="Services"
      />
      <q-tab name="processes" icon="fas fa-chart-area" label="Processes" />
      <q-tab
        v-if="$route.query.agentPlatform === 'windows'"
        name="eventlog"
        icon="fas fa-clipboard-list"
        label="Event Log"
      />
    </q-tabs>
    <q-separator />
    <q-tab-panels v-model="tab">
      <q-tab-panel name="terminal" class="q-pa-none">
        <iframe
          :src="terminal"
          :style="{
            height: `${$q.screen.height - 30}px`,
            width: `${$q.screen.width}px`,
          }"
        ></iframe>
      </q-tab-panel>
      <q-tab-panel name="processes" class="q-pa-none">
        <ProcessManager :agent_id="agent_id" />
      </q-tab-panel>
      <q-tab-panel
        v-if="$route.query.agentPlatform === 'windows'"
        name="services"
        class="q-pa-none"
      >
        <ServicesManager
          :agent_id="agent_id"
          :agentPlatform="$route.query.agentPlatform"
        />
      </q-tab-panel>
      <q-tab-panel
        v-if="$route.query.agentPlatform === 'windows'"
        name="eventlog"
        class="q-pa-none"
      >
        <EventLogManager
          :agent_id="agent_id"
          :agentPlatform="$route.query.agentPlatform"
        />
      </q-tab-panel>
      <q-tab-panel name="filebrowser" class="q-pa-none">
        <iframe
          :src="file"
          :style="{
            height: `${$q.screen.height - 30}px`,
            width: `${$q.screen.width}px`,
          }"
        ></iframe>
      </q-tab-panel>
    </q-tab-panels>
  </div>
</template>

<script>
// composition imports
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useQuasar, useMeta } from "quasar";
import { fetchAgentMeshCentralURLs } from "@/api/agents";
import { fetchDashboardInfo } from "@/api/core";

// ui imports
import ProcessManager from "@/components/agents/remotebg/ProcessManager.vue";
import ServicesManager from "@/components/agents/remotebg/ServicesManager.vue";
import EventLogManager from "@/components/agents/remotebg/EventLogManager.vue";

export default {
  name: "RemoteBackground",
  components: {
    ServicesManager,
    EventLogManager,
    ProcessManager,
  },
  setup() {
    // setup quasar
    const $q = useQuasar();

    // vue router
    const { params } = useRoute();

    // meshcentral tabs
    const terminal = ref("");
    const file = ref("");
    const tab = ref("terminal");

    const agent_id = computed(() => params.agent_id);

    async function getMeshURLs() {
      const data = await fetchAgentMeshCentralURLs(params.agent_id);
      terminal.value = data.terminal;
      file.value = data.file;
      useMeta({
        title: `${data.hostname} - ${data.client} - ${data.site} | Remote Background`,
      });
    }

    async function getDashInfo() {
      const { dark_mode } = await fetchDashboardInfo();
      $q.dark.set(dark_mode);
      $q.loadingBar.setDefaults({ size: "0px" });
    }

    // vue lifecycle hooks
    onMounted(() => {
      getDashInfo();
      getMeshURLs();
    });

    return {
      // reactive data
      terminal,
      file,
      tab,
      agent_id,
    };
  },
};
</script>
