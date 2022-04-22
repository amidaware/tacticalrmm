<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="min-width: 70vw">
      <q-bar>
        Script Output
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-card-section style="height: 70vh" class="scroll">
        <div>
          Last Run:
          <code>{{ formatDate(scriptInfo.last_run) }}</code>
          <br />Run Time:
          <code>{{ scriptInfo.execution_time }} seconds</code>
          <br />Return Code:
          <code>{{ scriptInfo.retcode }}</code>
          <br />
        </div>
        <br />
        <div v-if="scriptInfo.stdout">
          Standard Output
          <q-separator />
          <pre>{{ scriptInfo.stdout }}</pre>
        </div>
        <div v-if="scriptInfo.stderr">
          Standard Error
          <q-separator />
          <pre>{{ scriptInfo.stderr }}</pre>
        </div>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat dense push label="Cancel" v-close-popup />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { computed } from "vue";
import { useStore } from "vuex";
import { useDialogPluginComponent } from "quasar";

export default {
  name: "ScriptOutput",
  emits: [...useDialogPluginComponent.emits],
  props: { scriptInfo: !Object },
  setup(props) {
    // setup vuex
    const store = useStore();
    const formatDate = computed(() => store.getters.formatDate);

    // quasar dialog setup
    const { dialogRef, onDialogHide } = useDialogPluginComponent();

    return {
      // methods
      formatDate,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>