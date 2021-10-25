<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card style="min-width: 50vw">
      <q-bar>
        {{ agent.hostname }} Agent recovery
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form @submit="sendRecovery">
        <q-card-section>
          <div class="q-gutter-sm">
            <q-radio dense v-model="state.mode" val="mesh" label="Mesh Agent" />
            <q-radio dense v-model="state.mode" val="rpc" label="Tactical RPC" />
            <q-radio dense v-model="state.mode" val="tacagent" label="Tactical Agent" />
            <q-radio dense v-model="state.mode" val="command" label="Shell Command" />
          </div>
        </q-card-section>
        <q-card-section v-if="state.mode === 'mesh'">
          Fix issues with the Mesh Agent which handles take control, live terminal and file browser.
        </q-card-section>
        <q-card-section v-else-if="state.mode === 'tacagent'">
          Fix issues with the TacticalAgent windows service which handles agent check-in.
        </q-card-section>
        <q-card-section v-else-if="state.mode === 'rpc'">
          Fix issues with the Tactical RPC service which handles most of the agent's realtime functions and scheduled
          tasks.
        </q-card-section>
        <q-card-section v-else-if="state.mode === 'command'">
          <p>Run a shell command on the agent.</p>
          <p>You should use the 'Send Command' feature from the agent's context menu for sending shell commands.</p>
          <p>Only use this as a last resort if unable to recover the Tactical RPC service.</p>
          <q-input
            ref="input"
            v-model="state.cmd"
            outlined
            label="Command"
            bottom-slots
            stack-label
            error-message="*Required"
            :error="!isValid"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn dense flat push label="Cancel" v-close-popup />
          <q-btn :loading="loading" dense flat push label="Recover" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref, computed } from "vue";
import { useDialogPluginComponent } from "quasar";
import { sendAgentRecovery } from "@/api/agents";
import { notifySuccess } from "@/utils/notify";

export default {
  name: "AgentRecovery",
  emits: [...useDialogPluginComponent.emits],
  props: {
    agent: !Object,
  },
  setup(props) {
    // setup quasar dialog plugin
    const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();

    // agent recovery logic
    const state = ref({
      mode: "mesh",
      cmd: null,
    });

    const loading = ref(false);

    const isValid = computed(() => {
      if (state.value.mode === "command") {
        if (state.value.cmd === null || state.value.cmd === "") {
          return false;
        }
      }
      return true;
    });

    async function sendRecovery() {
      loading.value = true;
      try {
        const result = await sendAgentRecovery(props.agent.agent_id, state.value);
        notifySuccess(result);
        onDialogOK();
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    return {
      // reactive data
      state,
      loading,
      isValid,

      // methods
      sendRecovery,

      // dialog plugin
      dialogRef,
      onDialogHide,
    };
  },
};
</script>