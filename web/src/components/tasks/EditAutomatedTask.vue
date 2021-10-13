<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        Edit {{ task.name }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form @submit="submit">
        <q-card-section>
          <tactical-dropdown
            :rules="[val => !!val || '*Required']"
            v-model="state.script"
            label="Select script"
            :options="scriptOptions"
            outlined
            mapOptions
            disable
          />
        </q-card-section>
        <q-card-section>
          <q-select
            dense
            label="Script Arguments (press Enter after typing each argument)"
            filled
            v-model="state.script_args"
            use-input
            use-chips
            multiple
            hide-dropdown-icon
            input-debounce="0"
            new-value-mode="add"
          />
        </q-card-section>
        <q-card-section>
          <q-input
            :rules="[val => !!val || '*Required']"
            outlined
            dense
            v-model="state.name"
            label="Descriptive name of task"
            class="q-pb-none"
          />
        </q-card-section>
        <q-card-section>
          <tactical-dropdown
            v-model="state.alert_severity"
            :options="severityOptions"
            label="Alert Severity"
            outlined
            mapOptions
          />
        </q-card-section>
        <q-card-section>
          <q-checkbox dense label="Collector Task" v-model="collector" class="q-pb-sm" />
          <tactical-dropdown
            v-if="collector"
            :rules="[val => (collector && !!val) || '*Required']"
            v-model="state.custom_field"
            :options="customFieldOptions"
            label="Custom Field to update"
            outlined
            mapOptions
            :hint="
              state.collector_all_output
                ? 'All script output will be saved to custom field selected'
                : 'The last line of script output will be saved to custom field selected'
            "
          />
          <q-checkbox
            v-if="collector"
            dense
            label="Save all output"
            v-model="state.collector_all_output"
            class="q-py-sm"
          />
        </q-card-section>
        <q-card-section>
          <q-input
            :rules="[val => !!val || '*Required']"
            outlined
            dense
            v-model.number="state.timeout"
            type="number"
            label="Maximum permitted execution time (seconds)"
            class="q-pb-none"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn dense flat push label="Cancel" v-close-popup />
          <q-btn flat dense push label="Submit" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref, watch } from "vue";
import { useDialogPluginComponent } from "quasar";
import { updateTask } from "@/api/tasks";
import { useScriptDropdown } from "@/composables/scripts";
import { useCustomFieldDropdown } from "@/composables/core";
import { notifySuccess } from "@/utils/notify";

// ui imports
import TacticalDropdown from "@/components/ui/TacticalDropdown.vue";

// static data
const severityOptions = [
  { label: "Informational", value: "info" },
  { label: "Warning", value: "warning" },
  { label: "Error", value: "error" },
];

export default {
  name: "EditAutomatedTask",
  emits: [...useDialogPluginComponent.emits],
  components: { TacticalDropdown },
  props: {
    task: !Object,
  },
  setup(props) {
    // setup quasar dialog
    const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();

    // setup dropdowns
    const { scriptOptions } = useScriptDropdown(null, {
      onMount: true,
    });
    const { customFieldOptions } = useCustomFieldDropdown({ onMount: true });

    // edit automated task logic
    const task = ref(Object.assign({}, props.task));
    const collector = ref(!!task.value.custom_field);
    const loading = ref(false);

    watch(collector, (newValue, oldValue) => {
      task.value.custom_field = null;
      task.value.collector_all_output = false;
    });

    async function submit() {
      loading.value = true;

      try {
        // remove run_date_time
        delete task.value.run_date_time;
        const result = await updateTask(task.value.id, task.value);
        notifySuccess(result);
        onDialogOK();
      } catch (e) {
        console.error(e);
      }

      loading.value = false;
    }

    return {
      // reactive data
      state: task,
      collector,
      scriptOptions,
      customFieldOptions,

      // non reactive data
      severityOptions,

      // methods
      submit,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>