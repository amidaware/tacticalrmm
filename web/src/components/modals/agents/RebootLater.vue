<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="dialog-plugin" style="min-width: 30vw">
      <q-bar>
        Schedule reboot on {{ agent.hostname }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-card-section>
        <q-input
          type="datetime-local"
          dense
          label="Reboot time"
          stack-label
          filled
          v-model="state.datetime"
          hint="Uses the agent's local time zone"
        />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn dense flat push label="Cancel" v-close-popup />
        <q-btn :loading="loading" dense flat push label="Schedule Reboot" color="primary" @click="scheduleReboot" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref } from "vue";
import { useQuasar, useDialogPluginComponent, date } from "quasar";
import { scheduleAgentReboot } from "@/api/agents";
import { formatDateInputField } from "@/utils/format";

export default {
  name: "RebootLater",
  emits: [...useDialogPluginComponent.emits],
  props: {
    agent: !Object,
  },
  setup(props) {
    // setup quasar dialog plugin
    const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();
    const $q = useQuasar();

    // setup reboot later logic
    const state = ref({
      datetime: formatDateInputField(date.addToDate(Date.now(), { hours: 1 })),
    });
    const loading = ref(false);

    async function scheduleReboot() {
      loading.value = true;

      try {
        const result = await scheduleAgentReboot(props.agent.agent_id, state.value);
        $q.dialog({
          title: "Reboot pending",
          style: "width: 40vw",
          message: `A reboot has been scheduled for <strong>${state.value.datetime}</strong> on ${props.agent.hostname}.
            <br />It can be cancelled from the Pending Actions menu until the scheduled time.`,
          html: true,
        }).onDismiss(onDialogOK);
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    return {
      // reactive data
      state,
      loading,

      // methods
      scheduleReboot,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>