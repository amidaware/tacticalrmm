<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide" persistent>
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        Add Automated Task
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>

      <q-card-section v-if="scriptOptions.length === 0">
        <p>You need to upload a script first</p>
        <p>Settings -> Script Manager</p>
      </q-card-section>
      <q-stepper v-else v-model="step" ref="stepper" color="primary" animated>
        <q-step :name="1" title="Select Task" :done="step1Done" :error="!step1Done">
          <q-card-section>
            <tactical-dropdown
              :rules="[val => !!val || '*Required']"
              label="Select script"
              v-model="state.script"
              :options="scriptOptions"
              outlined
              mapOptions
              filterable
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
            <q-checkbox dense label="Collector Task" v-model="collector" class="q-pb-sm" />
            <tactical-dropdown
              v-if="collector"
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
            <tactical-dropdown
              v-model="state.alert_severity"
              :options="severityOptions"
              label="Alert Severity"
              outlined
              mapOptions
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
        </q-step>

        <q-step :name="2" title="Choose Schedule" :done="step2Done" :error="step > 1 && !step2Done">
          <q-radio v-model="state.task_type" val="scheduled" label="Scheduled" />
          <q-radio v-model="state.task_type" val="runonce" label="Run Once" />
          <q-radio v-model="state.task_type" val="checkfailure" label="On check failure" />
          <q-radio v-model="state.task_type" val="manual" label="Manual" />
          <div v-if="state.task_type === 'scheduled'" class="row q-pa-lg">
            <div class="col-3">
              Run on Days:
              <q-option-group :options="dayOptions" label="Days" type="checkbox" v-model="state.run_time_days" />
            </div>
            <div class="col-2"></div>
            <div class="col-6">
              At time:
              <q-time v-model="state.run_time_minute" />
            </div>
            <div class="col-1"></div>
          </div>
          <div v-if="state.task_type === 'runonce'" class="row q-pa-lg">
            <div class="col-11">
              <q-input filled v-model="state.run_time_date" hint="Agent timezone will be used">
                <template v-slot:append>
                  <q-icon name="event" class="cursor-pointer">
                    <q-popup-proxy transition-show="scale" transition-hide="scale">
                      <q-date v-model="state.run_time_date" mask="YYYY-MM-DD HH:mm">
                        <div class="row items-center justify-end">
                          <q-btn v-close-popup label="Close" color="primary" flat />
                        </div>
                      </q-date>
                    </q-popup-proxy>
                  </q-icon>
                  <q-icon name="access_time" class="cursor-pointer">
                    <q-popup-proxy transition-show="scale" transition-hide="scale">
                      <q-time v-model="state.run_time_date" mask="YYYY-MM-DD HH:mm">
                        <div class="row items-center justify-end">
                          <q-btn v-close-popup label="Close" color="primary" flat />
                        </div>
                      </q-time>
                    </q-popup-proxy>
                  </q-icon>
                </template>
              </q-input>
              <div class="q-gutter-sm">
                <q-checkbox v-model="state.remove_if_not_scheduled" label="Delete task after scheduled date" />
              </div>
              <div class="q-gutter-sm">
                <q-checkbox
                  v-model="state.run_asap_after_missed"
                  label="Run task ASAP after a scheduled start is missed (requires agent v1.4.7)"
                />
              </div>
            </div>
            <div class="col-1"></div>
          </div>
          <div v-else-if="state.task_type === 'checkfailure'" class="q-pa-lg">
            When Check Fails:
            <tactical-dropdown
              :rules="[val => !!val || '*Required']"
              v-model="state.assigned_check"
              outlined
              :options="checkOptions"
              label="Select Check"
              mapOptions
            />
          </div>
        </q-step>
      </q-stepper>
      <q-card-actions align="right">
        <q-btn dense flat push label="Cancel" v-close-popup />
        <q-btn v-if="step > 1" label="Back" @click="$refs.stepper.previous()" color="primary" flat dense push />
        <q-btn v-if="step !== 2" @click="step2($refs.stepper)" color="primary" label="Next" flat dense push />
        <q-btn
          v-else
          label="Add Task"
          :disable="!step1Done || !step2Done"
          color="primary"
          @click="submit"
          :loading="loading"
          flat
          dense
          push
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref, computed, watch, onMounted } from "vue";
import { useDialogPluginComponent } from "quasar";
import { saveTask } from "@/api/tasks";
import { useScriptDropdown } from "@/composables/scripts";
import { useCheckDropdown } from "@/composables/checks";
import { useCustomFieldDropdown } from "@/composables/core";
import { notifyError, notifySuccess } from "@/utils/notify";

// ui imports
import TacticalDropdown from "@/components/ui/TacticalDropdown.vue";

// static data
const severityOptions = [
  { label: "Informational", value: "info" },
  { label: "Warning", value: "warning" },
  { label: "Error", value: "error" },
];

const dayOptions = [
  { label: "Monday", value: "Monday" },
  { label: "Tuesday", value: "Tuesday" },
  { label: "Wednesday", value: "Wednesday" },
  { label: "Thursday", value: "Thursday" },
  { label: "Friday", value: "Friday" },
  { label: "Saturday", value: "Saturday" },
  { label: "Sunday", value: "Sunday" },
];

export default {
  components: { TacticalDropdown },
  name: "AddAutomatedTask",
  emits: [...useDialogPluginComponent.emits],
  props: {
    parent: !Object,
  },
  setup(props) {
    // setup quasar dialog
    const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();

    // setup dropdowns
    const { script, scriptOptions, defaultTimeout, defaultArgs } = useScriptDropdown(undefined, {
      onMount: true,
    });
    const { checkOptions, getCheckOptions } = useCheckDropdown();
    const { customFieldOptions } = useCustomFieldDropdown({ onMount: true });

    // add task logic
    const task = ref({
      ...props.parent,
      script,
      script_args: defaultArgs,
      timeout: defaultTimeout,
      assigned_check: null,
      custom_field: null,
      name: null,
      run_time_days: [],
      run_time_minute: null,
      run_time_date: null,
      remove_if_not_scheduled: false,
      run_asap_after_missed: true,
      task_type: "scheduled",
      alert_severity: "info",
      collector_all_output: false,
    });

    const collector = ref(false);
    const loading = ref(false);

    async function submit() {
      if (!step1Done.value || !step2Done.value) {
        notifyError("Some steps are incomplete");
        return;
      } else {
        loading.value = true;
        try {
          const result = await saveTask(task.value);
          notifySuccess(result);
          onDialogOK();
        } catch (e) {
          console.error(e);
        }
        loading.value = false;
      }
    }

    watch(
      () => task.value.task_type,
      (newValue, oldValue) => {
        task.value.assigned_check = null;
        task.value.run_time_days = [];
        task.value.run_time_minute = null;
        task.value.run_time_date = null;
        task.value.remove_if_not_scheduled = false;
      }
    );

    watch(collector, (newValue, oldValue) => {
      task.value.custom_field = null;
      task.value.collector_all_ouput = false;
    });

    // stepper logic
    const step = ref(1);
    const step1Done = computed(() => {
      return (
        (!!script.value && !!task.value.name && !!defaultTimeout.value && !collector.value) ||
        (!!script.value && !!task.value.name && !!defaultTimeout.value && collector.value && !!task.value.custom_field)
      );
    });

    const step2Done = computed(() => {
      if (task.value.task_type === "scheduled") {
        return task.value.run_time_days.length !== 0 && !!task.value.run_time_minute;
      } else if (task.value.task_type === "checkfailure") {
        return !!task.value.assigned_check;
      } else if (task.value.task_type === "manual") {
        return true;
      } else if (task.value.task_type === "runonce") {
        return !!task.value.run_time_date;
      } else {
        return false;
      }
    });

    function step2(stepper) {
      if (step1Done.value) {
        stepper.next();
      } else {
        if (!script.value) notifyError("Script field is required");
        else if (!task.value.name) notifyError("Name field is required");
        else if (!defaultTimeout.value) notifyError("Timeout field is required");
        else if (collector.value && !task.value.custom_field) notifyError("You must select a custom field");
      }
    }

    onMounted(() => {
      getCheckOptions(props.parent);
    });

    return {
      // reactive data
      state: task,
      collector,
      loading,
      step,
      scriptOptions,
      checkOptions,
      customFieldOptions,
      step2,
      step1Done,
      step2Done,

      // non-reactive data
      severityOptions,
      dayOptions,

      // methods
      submit,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>