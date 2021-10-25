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
        <q-input dense filled v-model="state.datetime">
          <template v-slot:prepend>
            <q-icon name="event" class="cursor-pointer">
              <q-popup-proxy transition-show="scale" transition-hide="scale">
                <q-date v-model="state.datetime" mask="YYYY-MM-DD HH:mm" />
              </q-popup-proxy>
            </q-icon>
          </template>

          <template v-slot:append>
            <q-icon name="access_time" class="cursor-pointer">
              <q-popup-proxy transition-show="scale" transition-hide="scale">
                <q-time v-model="state.datetime" mask="YYYY-MM-DD HH:mm" />
              </q-popup-proxy>
            </q-icon>
          </template>
        </q-input>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn dense flat push label="Cancel" v-close-popup />
        <q-btn dense flat push label="Schedule Reboot" color="primary" @click="scheduleReboot" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref } from "vue";
import { useQuasar, useDialogPluginComponent } from "quasar";
import { scheduleAgentReboot } from "@/api/agents";
import { date } from "quasar";

export default {
  name: "RebootLater",
  emits: [...useDialogPluginComponent.emits],
  props: {
    agent: !Object,
  },
  setup(props) {
    // setup quasar dialog plugin
    const { dialogRef, onDialogHide } = useDialogPluginComponent();
    const $q = useQuasar();

    // setup reboot later logic
    const state = ref({
      datetime: date.formatDate(Date.now(), "YYYY-MM-DD HH:mm"),
    });
    const loading = ref(false);

    async function scheduleReboot() {
      loading.value = true;

      try {
        const result = await scheduleAgentReboot(props.agent.agent_id, { datetime: state.value.datetime });

        $q.dialog({
          title: "Reboot pending",
          style: "width: 40vw",
          message: `A reboot has been scheduled for <strong>${state.value.datetime}</strong> on ${props.agent.agent_id}.
            <br />It can be cancelled from the Pending Actions menu until the scheduled time.`,
          html: true,
        });
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