<template>
  <div>
    <q-bar>
      <span class="text-caption">
        Agent Status:
        <q-badge :color="statusColor" :label="status" />
      </span>
      <q-space />
      <q-btn
        class="q-mr-md"
        color="primary"
        size="sm"
        label="Restart Connection"
        icon="refresh"
        @click="restartMeshService"
      />
      <q-btn color="negative" size="sm" label="Recover Connection" icon="fas fa-first-aid" @click="repairMeshCentral" />
      <q-space />
    </q-bar>

    <q-video v-show="control" :src="control" :style="{ height: `${$q.screen.height - 26}px` }"></q-video>
  </div>
</template>

<script>
// composition imports
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useMeta, useQuasar } from "quasar";
import { fetchAgentMeshCentralURLs, sendAgentRecoverMesh } from "@/api/agents";
import { fetchDashboardInfo } from "@/api/core";
import { sendAgentServiceAction } from "@/api/services";
import { notifySuccess } from "@/utils/notify";

export default {
  name: "TakeControl",
  setup(props) {
    // vue lifecycle hooks
    onMounted(() => {
      getDashInfo();
      getMeshURLs();
    });

    // quasar setup
    const $q = useQuasar();

    // vue router
    const { params } = useRoute();

    // take control setup
    const control = ref("");
    const status = ref(null);

    const statusColor = computed(() => {
      if (status.value) {
        switch (status.value) {
          case "online":
            return "positive";
          case "offline":
            return "warning";
          case "overdue":
            return "negative";
        }
      } else return "negative";
    });

    async function getMeshURLs() {
      $q.loading.show();
      try {
        const data = await fetchAgentMeshCentralURLs(params.agent_id);
        control.value = data.control;
        status.value = data.status;
        useMeta({ title: `${data.hostname} - ${data.client} - ${data.site} | Remote Background` });
      } catch (e) {
        console.error(e);
      }
      $q.loading.hide();
    }

    async function getDashInfo() {
      const { dark_mode, loading_bar_color } = await fetchDashboardInfo();
      $q.dark.set(dark_mode);
      $q.loadingBar.setDefaults({ color: loading_bar_color });
    }

    async function repairMeshCentral() {
      control.value = "";
      $q.loading.show({ message: "Attempting to repair Mesh Agent" });
      try {
        const data = await sendAgentRecoverMesh(params.agent_id);
        await getMeshURLs();
        setTimeout(() => {
          notifySuccess(data);
        }, 500);
      } catch (e) {
        console.error(e);
      }
      $q.loading.hide();
    }

    async function restartMeshService() {
      $q.loading.show({ message: "Restarting Mesh Agent" });
      const data = {
        sv_action: "restart",
      };

      try {
        await sendAgentServiceAction(params.agent_id, "mesh agent", data);
        setTimeout(() => {
          notifySuccess("Mesh agent service was restarted");
        }, 500);
      } catch (e) {
        console.error(e);
      }

      $q.loading.hide();
    }

    return {
      // reactive data
      control,
      status,
      statusColor,

      // methods
      repairMeshCentral,
      restartMeshService,
    };
  },
};
</script>