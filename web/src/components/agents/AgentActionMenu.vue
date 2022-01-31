<template>
  <q-list dense style="min-width: 200px">
    <!-- edit agent -->
    <q-item clickable v-close-popup @click="showEditAgent(agent.agent_id)">
      <q-item-section side>
        <q-icon size="xs" name="fas fa-edit" />
      </q-item-section>
      <q-item-section>Edit {{ agent.hostname }}</q-item-section>
    </q-item>
    <!-- agent pending actions -->
    <q-item clickable v-close-popup @click="showPendingActionsModal(agent)">
      <q-item-section side>
        <q-icon size="xs" name="far fa-clock" />
      </q-item-section>
      <q-item-section>Pending Agent Actions</q-item-section>
    </q-item>
    <!-- take control -->
    <q-item clickable v-ripple v-close-popup @click="runTakeControl(agent.agent_id)">
      <q-item-section side>
        <q-icon size="xs" name="fas fa-desktop" />
      </q-item-section>

      <q-item-section>Take Control</q-item-section>
    </q-item>

    <q-item clickable v-ripple @click="getURLActions">
      <q-item-section side>
        <q-icon size="xs" name="open_in_new" />
      </q-item-section>
      <q-item-section>Run URL Action</q-item-section>
      <q-item-section side>
        <q-icon name="keyboard_arrow_right" />
      </q-item-section>
      <q-menu auto-close anchor="top end" self="top start">
        <q-list>
          <q-item
            v-for="action in urlActions"
            :key="action.id"
            dense
            clickable
            v-close-popup
            @click="runURLAction({ agent_id: agent.agent_id, action: action.id })"
          >
            {{ action.name }}
          </q-item>
        </q-list>
      </q-menu>
    </q-item>

    <q-item clickable v-ripple v-close-popup @click="showSendCommand(agent)">
      <q-item-section side>
        <q-icon size="xs" name="fas fa-terminal" />
      </q-item-section>
      <q-item-section>Send Command</q-item-section>
    </q-item>

    <q-item clickable v-ripple v-close-popup @click="showRunScript(agent)">
      <q-item-section side>
        <q-icon size="xs" name="fas fa-terminal" />
      </q-item-section>
      <q-item-section>Run Script</q-item-section>
    </q-item>

    <q-item clickable v-ripple @click="getFavoriteScripts">
      <q-item-section side>
        <q-icon size="xs" name="star" />
      </q-item-section>
      <q-item-section>Run Favorited Script</q-item-section>
      <q-item-section side>
        <q-icon name="keyboard_arrow_right" />
      </q-item-section>
      <q-menu auto-close anchor="top end" self="top start">
        <q-list>
          <q-item
            v-for="script in favoriteScripts"
            :key="script.value"
            dense
            clickable
            v-close-popup
            @click="showRunScript(agent, script.value)"
          >
            {{ script.label }}
          </q-item>
        </q-list>
      </q-menu>
    </q-item>

    <q-item clickable v-close-popup @click="runRemoteBackground(agent.agent_id)">
      <q-item-section side>
        <q-icon size="xs" name="fas fa-cogs" />
      </q-item-section>
      <q-item-section>Remote Background</q-item-section>
    </q-item>

    <!-- maintenance mode -->
    <q-item clickable v-close-popup @click="toggleMaintenance(agent)">
      <q-item-section side>
        <q-icon size="xs" name="construction" />
      </q-item-section>
      <q-item-section>
        {{ agent.maintenance_mode ? "Disable Maintenance Mode" : "Enable Maintenance Mode" }}
      </q-item-section>
    </q-item>

    <!-- patch management -->
    <q-item clickable>
      <q-item-section side>
        <q-icon size="xs" name="system_update" />
      </q-item-section>
      <q-item-section>Patch Management</q-item-section>
      <q-item-section side>
        <q-icon name="keyboard_arrow_right" />
      </q-item-section>

      <q-menu auto-close anchor="top right" self="top left">
        <q-list dense style="min-width: 100px">
          <q-item clickable v-ripple @click="runPatchStatusScan(agent)">
            <q-item-section>Run Patch Status Scan</q-item-section>
          </q-item>
          <q-item clickable v-ripple @click="installPatches(agent)">
            <q-item-section>Install Patches Now</q-item-section>
          </q-item>
        </q-list>
      </q-menu>
    </q-item>

    <q-item clickable v-close-popup @click="runChecks(agent)">
      <q-item-section side>
        <q-icon size="xs" name="fas fa-check-double" />
      </q-item-section>
      <q-item-section>Run Checks</q-item-section>
    </q-item>

    <q-item clickable>
      <q-item-section side>
        <q-icon size="xs" name="power_settings_new" />
      </q-item-section>
      <q-item-section>Reboot</q-item-section>
      <q-item-section side>
        <q-icon name="keyboard_arrow_right" />
      </q-item-section>

      <q-menu auto-close anchor="top right" self="top left">
        <q-list dense style="min-width: 100px">
          <!-- reboot now -->
          <q-item clickable v-ripple @click="rebootNow(agent)">
            <q-item-section>Now</q-item-section>
          </q-item>
          <!-- reboot later -->
          <q-item clickable v-ripple @click="showRebootLaterModal(agent)">
            <q-item-section>Later</q-item-section>
          </q-item>
        </q-list>
      </q-menu>
    </q-item>

    <q-item clickable v-close-popup @click="showPolicyAdd(agent)">
      <q-item-section side>
        <q-icon size="xs" name="policy" />
      </q-item-section>
      <q-item-section>Assign Automation Policy</q-item-section>
    </q-item>

    <q-item clickable v-close-popup @click="showAgentRecovery(agent)">
      <q-item-section side>
        <q-icon size="xs" name="fas fa-first-aid" />
      </q-item-section>
      <q-item-section>Agent Recovery</q-item-section>
    </q-item>

    <q-item clickable v-close-popup @click="pingAgent(agent)">
      <q-item-section side>
        <q-icon size="xs" name="delete" />
      </q-item-section>
      <q-item-section>Remove Agent</q-item-section>
    </q-item>

    <q-separator />
    <q-item clickable v-close-popup>
      <q-item-section>Close</q-item-section>
    </q-item>
  </q-list>
</template>

<script>
// composition imports
import { ref, inject } from "vue";
import { useStore } from "vuex";
import { useQuasar } from "quasar";
import { fetchURLActions, runURLAction } from "@/api/core";
import {
  editAgent,
  agentRebootNow,
  sendAgentPing,
  removeAgent,
  runRemoteBackground,
  runTakeControl,
} from "@/api/agents";
import { runAgentUpdateScan, runAgentUpdateInstall } from "@/api/winupdates";
import { runAgentChecks } from "@/api/checks";
import { fetchScripts } from "@/api/scripts";
import { notifySuccess, notifyWarning, notifyError } from "@/utils/notify";

// ui imports
import PendingActions from "@/components/logs/PendingActions";
import AgentRecovery from "@/components/modals/agents/AgentRecovery";
import PolicyAdd from "@/components/automation/modals/PolicyAdd";
import RebootLater from "@/components/modals/agents/RebootLater";
import EditAgent from "@/components/modals/agents/EditAgent";
import SendCommand from "@/components/modals/agents/SendCommand";
import RunScript from "@/components/modals/agents/RunScript";

export default {
  name: "AgentActionMenu",
  props: {
    agent: !Object,
  },
  setup(props) {
    const $q = useQuasar();
    const store = useStore();

    const refreshDashboard = inject("refreshDashboard");

    const urlActions = ref([]);
    const favoriteScripts = ref([]);
    const menuLoading = ref(false);

    function showEditAgent(agent_id) {
      $q.dialog({
        component: EditAgent,
        componentProps: {
          agent_id: agent_id,
        },
      }).onOk(refreshDashboard);
    }

    function showPendingActionsModal(agent) {
      $q.dialog({
        component: PendingActions,
        componentProps: {
          agent: agent,
        },
      });
    }

    async function getURLActions() {
      menuLoading.value = true;
      try {
        urlActions.value = await fetchURLActions();

        if (urlActions.value.length === 0) {
          notifyWarning("No URL Actions configured. Go to Settings > Global Settings > URL Actions");
          return;
        }
      } catch (e) {}
      menuLoading.value = true;
    }

    function showSendCommand(agent) {
      $q.dialog({
        component: SendCommand,
        componentProps: {
          agent: agent,
        },
      });
    }

    function showRunScript(agent, script = undefined) {
      $q.dialog({
        component: RunScript,
        componentProps: {
          agent,
          script,
        },
      });
    }

    async function getFavoriteScripts() {
      favoriteScripts.value = [];

      menuLoading.value = true;
      try {
        const data = await fetchScripts({ showCommunityScripts: store.state.showCommunityScripts });

        const scripts = data.filter(script => !!script.favorite);

        if (scripts.length === 0) {
          notifyWarning("You don't have any scripts favorited!");
          return;
        }

        favoriteScripts.value = scripts
          .map(script => ({
            label: script.name,
            value: script.id,
            timeout: script.default_timeout,
            args: script.args,
          }))
          .sort((a, b) => a.label.localeCompare(b.label));
      } catch (e) {
        console.error(e);
      }
    }

    async function toggleMaintenance(agent) {
      let data = {
        maintenance_mode: !agent.maintenance_mode,
      };

      try {
        const result = await editAgent(agent.agent_id, data);
        notifySuccess(`Maintenance mode was ${agent.maintenance_mode ? "disabled" : "enabled"} on ${agent.hostname}`);
        store.commit("setRefreshSummaryTab", true);
        refreshDashboard();
      } catch (e) {
        console.error(e);
      }
    }

    async function runPatchStatusScan(agent) {
      try {
        const result = await runAgentUpdateScan(agent.agent_id);
        notifySuccess(`Scan will be run shortly on ${agent.hostname}`);
      } catch (e) {
        console.error(e);
      }
    }

    async function installPatches(agent) {
      try {
        const data = await runAgentUpdateInstall(agent.agent_id);
        notifySuccess(data);
      } catch (e) {
        console.error(e);
      }
    }

    async function runChecks(agent) {
      try {
        const data = await runAgentChecks(agent.agent_id);
        notifySuccess(data);
      } catch (e) {
        console.error(e);
      }
    }

    function showRebootLaterModal(agent) {
      $q.dialog({
        component: RebootLater,
        componentProps: {
          agent: agent,
        },
      }).onOk(refreshDashboard);
    }

    function rebootNow(agent) {
      $q.dialog({
        title: "Are you sure?",
        message: `Reboot ${agent.hostname} now`,
        cancel: true,
        persistent: true,
      }).onOk(async () => {
        $q.loading.show();
        try {
          const result = await agentRebootNow(agent.agent_id);
          notifySuccess(`${agent.hostname} will now be restarted`);
          $q.loading.hide();
        } catch (e) {
          $q.loading.hide();
          console.error(e);
        }
      });
    }

    function showPolicyAdd(agent) {
      $q.dialog({
        component: PolicyAdd,
        componentProps: {
          type: "agent",
          object: agent,
        },
      }).onOk(refreshDashboard);
    }

    function showAgentRecovery(agent) {
      $q.dialog({
        component: AgentRecovery,
        componentProps: {
          agent: agent,
        },
      });
    }

    async function pingAgent(agent) {
      try {
        $q.loading.show();
        const data = await sendAgentPing(agent.agent_id);
        $q.loading.hide();
        if (data.status === "offline") {
          $q.dialog({
            title: "Agent offline",
            message: `${agent.hostname} cannot be contacted. 
                  Would you like to continue with the uninstall? 
                  If so, the agent will need to be manually uninstalled from the computer.`,
            cancel: { label: "No", color: "negative" },
            ok: { label: "Yes", color: "positive" },
            persistent: true,
          })
            .onOk(() => deleteAgent(agent))
            .onCancel(() => {
              return;
            });
        } else if (data.status === "online") {
          deleteAgent(agent);
        } else {
          notifyError("Something went wrong");
        }
      } catch (e) {
        $q.loading.hide();
        console.error(e);
      }
    }

    function deleteAgent(agent) {
      $q.dialog({
        title: `Please type <code style="color:red">yes</code> in the box below to confirm deletion.`,
        prompt: {
          model: "",
          type: "text",
          isValid: val => val === "yes",
        },
        cancel: true,
        ok: { label: "Uninstall", color: "negative" },
        persistent: true,
        html: true,
      }).onOk(async val => {
        try {
          const data = await removeAgent(agent.agent_id);
          notifySuccess(data);
          refreshDashboard(false /* clearTreeSelected */, true /* clearSubTable */);
        } catch (e) {
          console.error(e);
        }
      });
    }

    return {
      // reactive data
      urlActions,
      favoriteScripts,

      // methods
      showEditAgent,
      showPendingActionsModal,
      runTakeControl,
      runRemoteBackground,
      getURLActions,
      runURLAction,
      showSendCommand,
      showRunScript,
      getFavoriteScripts,
      toggleMaintenance,
      runPatchStatusScan,
      installPatches,
      runChecks,
      showRebootLaterModal,
      rebootNow,
      showPolicyAdd,
      showAgentRecovery,
      pingAgent,
    };
  },
};
</script>