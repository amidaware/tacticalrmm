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

      <q-form @submit.prevent="submit">
        <div style="max-height: 70vh" class="scroll">
          <q-card-section>
            <!-- policy check, either choose from a list of default services or enter manually -->
            <q-radio
              v-if="isPolicy && !check"
              v-model="localCheck.svc_policy_mode"
              val="default"
              label="Choose from defaults"
            />
            <q-radio
              v-if="isPolicy && !check"
              v-model="localCheck.svc_policy_mode"
              val="manual"
              label="Enter manually"
            />
            <q-select
              v-if="isPolicy && localCheck.svc_policy_mode === 'default' && !check"
              :rules="[val => !!val || '*Required']"
              dense
              options-dense
              outlined
              v-model="localCheck.svc_name"
              :options="serviceOptions"
              label="Service"
              map-options
              emit-value
              :disable="!!check"
            />
            <q-input
              v-if="isPolicy && localCheck.svc_policy_mode === 'manual'"
              :rules="[val => !!val || '*Required']"
              outlined
              dense
              v-model="localCheck.svc_name"
              label="Service Name"
            />
            <q-input
              v-if="isPolicy && localCheck.svc_policy_mode === 'manual'"
              :rules="[val => !!val || '*Required']"
              outlined
              dense
              v-model="localCheck.svc_display_name"
              label="Display Name"
            />
            <!-- agent check -->
            <!-- disable selection if editing -->
            <q-select
              v-if="isAgent"
              :rules="[val => !!val || '*Required']"
              dense
              options-dense
              outlined
              v-model="localCheck.svc_name"
              :options="serviceOptions"
              label="Service"
              map-options
              emit-value
              :disable="!!check"
            />
          </q-card-section>
          <q-card-section>
            <q-checkbox v-model="localCheck.pass_if_start_pending" label="PASS if service is in 'Start Pending' mode" />
            <br />
            <q-checkbox v-model="localCheck.pass_if_svc_not_exist" label="PASS if service doesn't exist" />
            <br />
            <q-checkbox v-model="localCheck.restart_if_stopped" label="Restart service if it's stopped" />
          </q-card-section>
          <q-card-section>
            <q-select
              outlined
              dense
              options-dense
              map-options
              emit-value
              v-model="localCheck.alert_severity"
              :options="severityOptions"
              label="Alert Severity"
            />
          </q-card-section>
          <q-card-section>
            <q-select
              outlined
              dense
              options-dense
              v-model="localCheck.fails_b4_alert"
              :options="failOptions"
              label="Number of consecutive failures before alert"
            />
          </q-card-section>
          <q-card-section>
            <q-input
              dense
              outlined
              type="number"
              v-model.number="localCheck.run_interval"
              label="Run this check every (seconds)"
              hint="Setting this value to anything other than 0 will override the 'Run checks every' setting on the agent"
            />
          </q-card-section>
        </div>
        <q-card-actions align="right">
          <q-btn dense flat label="Cancel" v-close-popup />
          <q-btn :loading="loading" dense flat label="Save" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { computed, watch } from "vue";
import { useDialogPluginComponent } from "quasar";
import { useCheckModal } from "@/composables/checks";

export default {
  name: "WinSvcCheck",
  emits: [...useDialogPluginComponent.emits],
  props: {
    check: Object,
    parent: Object, // {agent: agent.agent_id} or {policy: policy.id}
  },
  setup(props) {
    // setup quasar dialog
    const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();

    // check logic
    const { check, loading, submit, failOptions, severityOptions, serviceOptions } = useCheckModal({
      editCheck: props.check,
      initialState: {
        ...props.parent,
        check_type: "winsvc",
        svc_name: null,
        svc_display_name: null,
        svc_policy_mode: null,
        pass_if_start_pending: false,
        pass_if_svc_not_exist: false,
        restart_if_stopped: false,
        fails_b4_alert: 1,
        alert_severity: "warning",
        run_interval: 0,
      },
      onDialogOK,
    });

    watch(
      () => check.value.svc_name,
      (newvalue, oldValue) => {
        check.value.svc_display_name = serviceOptions.value.find(i => i.value === check.value.svc_name).label;
      }
    );

    watch(
      () => check.value.svc_policy_mode,
      (newValue, oldValue) => {
        check.value.svc_name = null;
        check.value.svc_display_name = null;
      }
    );

    const isPolicy = computed(() => {
      if (props.check) return !!props.check.policy;
      else return !!props.parent.policy;
    });

    const isAgent = computed(() => {
      if (props.check) return !!props.check.agent;
      else return !!props.parent.agent;
    });

    return {
      // reactive data
      localCheck: check,
      loading,
      isPolicy,
      isAgent,

      // non-reactive data
      failOptions,
      severityOptions,
      serviceOptions,

      // methods
      submit,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>