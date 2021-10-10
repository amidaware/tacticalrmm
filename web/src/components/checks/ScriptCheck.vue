<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        {{ check ? `Edit Script Check` : "Add Script Check" }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-card-section v-if="scriptOptions.length === 0">
        <p>You need to upload a script first</p>
        <p>Settings -> Script Manager</p>
      </q-card-section>

      <q-form v-else @submit.prevent="beforeSubmit">
        <q-card-section>
          <tactical-dropdown
            :rules="[val => !!val || '*Required']"
            outlined
            v-model="script"
            :options="scriptOptions"
            label="Select script"
            mapOptions
            :disable="!!check"
          />
        </q-card-section>
        <q-card-section>
          <q-select
            dense
            label="Script Arguments (press Enter after typing each argument)"
            filled
            v-model="args"
            use-input
            use-chips
            multiple
            hide-dropdown-icon
            input-debounce="0"
            new-value-mode="add"
          />
        </q-card-section>
        <q-card-section>
          <tactical-dropdown
            label="Informational return codes (press Enter after typing each code)"
            filled
            v-model="localCheck.info_return_codes"
            multiple
            hide-dropdown-icon
            use-input
            input-debounce="0"
            new-value-mode="add-unique"
            @new-value="validateRetcode"
          />
        </q-card-section>
        <q-card-section>
          <tactical-dropdown
            label="Warning return codes (press Enter after typing each code)"
            filled
            v-model="localCheck.warning_return_codes"
            use-input
            multiple
            hide-dropdown-icon
            input-debounce="0"
            new-value-mode="add-unique"
            @new-value="validateRetcode"
          />
        </q-card-section>
        <q-card-section>
          <q-input outlined dense v-model.number="timeout" label="Script Timeout (seconds)" />
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
            outlined
            dense
            type="number"
            v-model.number="localCheck.run_interval"
            label="Run this check every (seconds)"
            hint="Setting this value to anything other than 0 will override the 'Run checks every' setting on the agent"
          />
        </q-card-section>
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
import { computed, onMounted } from "vue";
import { useStore } from "vuex";
import { useDialogPluginComponent } from "quasar";
import { useCheckModal } from "@/composables/checks";
import { useScriptDropdown } from "@/composables/scripts";
import { validateRetcode } from "@/utils/validation";

// ui imports
import TacticalDropdown from "@/components/ui/TacticalDropdown.vue";

export default {
  components: { TacticalDropdown },
  name: "ScriptCheck",
  emits: [...useDialogPluginComponent.emits],
  props: {
    check: Object,
    parent: Object, // {agent: agent.agent_id} or {policy: policy.id}
  },
  setup(props) {
    // setup vuex
    const store = useStore();
    const showCommunityScripts = computed(() => store.state.showCommunityScripts);

    // setup quasar dialog
    const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();

    // setup script dropdown
    const { script, scriptOptions, defaultTimeout, defaultArgs, getScriptOptions } = useScriptDropdown(undefined, true);

    // check logic

    // set script if editing
    if (props.check) {
      script.value = props.check.script;
    }

    const { check, loading, submit, failOptions, severityOptions } = useCheckModal({
      editCheck: props.check,
      initialState: {
        ...props.parent,
        check_type: "script",
        fails_b4_alert: 1,
        info_return_codes: [],
        warning_return_codes: [],
        run_interval: 0,
      },
      onDialogOK,
    });

    function beforeSubmit() {
      check.value.script = script.value;
      check.value.script_args = defaultArgs.value;
      check.value.timeout = defaultTimeout.value;

      submit();
    }

    onMounted(() => {
      getScriptOptions(showCommunityScripts.value);
    });

    return {
      // reactive data
      localCheck: check,
      loading,
      script,
      timeout: defaultTimeout,
      args: defaultArgs,

      // non-reactive data
      failOptions,
      scriptOptions,
      severityOptions,

      // methods
      beforeSubmit,
      validateRetcode,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>