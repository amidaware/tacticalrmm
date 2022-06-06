<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        {{ check ? `Edit Memory Check` : "Add Memory Check" }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form @submit.prevent="submit(onDialogOK)">
        <div style="max-height: 70vh" class="scroll">
          <q-card-section>
            <q-input
              dense
              outlined
              type="number"
              v-model.number="state.warning_threshold"
              label="Warning Threshold (%)"
              :rules="[
                (val) => val >= 0 || 'Minimum threshold is 0',
                (val) => val < 100 || 'Maximum threshold is 99',
              ]"
            />
          </q-card-section>
          <q-card-section>
            <q-input
              dense
              outlined
              type="number"
              v-model.number="state.error_threshold"
              label="Error Threshold (%)"
              :rules="[
                (val) => val >= 0 || 'Minimum threshold is 0',
                (val) => val < 100 || 'Maximum threshold is 99',
              ]"
            />
          </q-card-section>
          <q-card-section>
            <q-select
              outlined
              dense
              options-dense
              v-model="state.fails_b4_alert"
              :options="failOptions"
              label="Number of consecutive failures before alert"
            />
          </q-card-section>
          <q-card-section>
            <q-input
              outlined
              dense
              type="number"
              v-model.number="state.run_interval"
              label="Run this check every (seconds)"
              hint="Setting this value to anything other than 0 will override the 'Run checks every' setting on the agent"
            />
          </q-card-section>
        </div>
        <q-card-actions align="right">
          <q-btn dense flat label="Cancel" v-close-popup />
          <q-btn
            :loading="loading"
            dense
            flat
            label="Save"
            color="primary"
            type="submit"
          />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { useDialogPluginComponent } from "quasar";
import { useCheckModal } from "@/composables/checks";

export default {
  name: "MemCheck",
  emits: [...useDialogPluginComponent.emits],
  props: {
    check: Object,
    parent: Object, // {agent: agent.agent_id} or {policy: policy.id}
  },
  setup(props) {
    // setup quasar dialog
    const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();

    // check logic
    const { state, loading, submit, failOptions } = useCheckModal({
      editCheck: props.check,
      initialState: {
        ...props.parent,
        check_type: "memory",
        warning_threshold: 70,
        error_threshold: 85,
        fails_b4_alert: 1,
        run_interval: 0,
      },
    });

    return {
      // reactive data
      state,
      loading,

      // non-reactive data
      failOptions,

      // methods
      submit,

      // quasar dialog
      dialogRef,
      onDialogHide,
      onDialogOK,
    };
  },
};
</script>
