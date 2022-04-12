<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide" persistent>
    <q-card class="q-dialog-plugin" style="width: 65vw; min-width: 65vw">
      <q-bar>
        {{ task ? `Editing Automated Task: ${task.name}` : "Adding Automated Task" }}
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
        <q-step :name="1" title="Select Task" :done="step > 1" :error="!isValidStep1">
          <q-form @submit.prevent ref="taskGeneralForm">
            <q-card-section>
              <q-input
                :rules="[val => !!val || '*Required']"
                filled
                dense
                v-model="state.name"
                label="Descriptive name of task"
                hide-bottom-space
              />
            </q-card-section>
            <q-card-section>
              <q-checkbox
                dense
                label="Collector Task"
                v-model="collector"
                class="q-pb-sm"
                @update:model-value="
                  state.custom_field = null;
                  state.collector_all_output = false;
                "
              />
              <tactical-dropdown
                v-if="collector"
                :rules="[val => !!val || '*Required']"
                v-model="state.custom_field"
                :options="customFieldOptions"
                label="Custom Field to update"
                filled
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
                filled
                mapOptions
                :rules="[val => !!val || '*Required']"
              />
            </q-card-section>
          </q-form>
        </q-step>

        <q-step :name="2" title="Configure Actions" :done="step > 2" :error="!isValidStep2">
          <q-form @submit.prevent="addAction">
            <div class="row q-pa-sm q-gutter-x-xs items-center">
              <div class="text-subtitle2 col-12">Action Type:</div>
              <q-option-group
                class="col-12"
                inline
                v-model="actionType"
                :options="[
                  { label: 'Script', value: 'script' },
                  { label: 'Command', value: 'cmd' },
                ]"
              />

              <tactical-dropdown
                v-if="actionType === 'script'"
                class="col-4"
                label="Select script"
                v-model="script"
                :options="scriptOptions"
                filled
                mapOptions
                filterable
              />

              <q-select
                v-if="actionType === 'script'"
                class="col-5"
                dense
                label="Script Arguments (press Enter after typing each argument)"
                filled
                v-model="defaultArgs"
                use-input
                use-chips
                multiple
                hide-dropdown-icon
                input-debounce="0"
                new-value-mode="add"
              />

              <q-input
                v-if="actionType === 'script'"
                class="col-2"
                filled
                dense
                v-model.number="defaultTimeout"
                type="number"
                label="Timeout (seconds)"
              />

              <q-input v-if="actionType === 'cmd'" label="Command" v-model="command" dense filled class="col-7" />
              <q-input
                v-if="actionType === 'cmd'"
                class="col-2"
                filled
                dense
                v-model.number="defaultTimeout"
                type="number"
                label="Timeout (seconds)"
              />
              <q-option-group
                v-if="actionType === 'cmd'"
                class="col-2 q-pl-sm"
                inline
                v-model="shell"
                :options="[
                  { label: 'Batch', value: 'cmd' },
                  { label: 'Powershell', value: 'powershell' },
                ]"
              />
              <q-btn class="col-1" type="submit" style="width: 50px" flat dense icon="add" color="primary" />
            </div>
          </q-form>
          <div class="text-subtitle2 q-pa-sm">
            Actions:
            <q-checkbox class="float-right" label="Continue on Errors" v-model="state.continue_on_error" dense>
              <q-tooltip>Continue task if an action fails</q-tooltip>
            </q-checkbox>
          </div>
          <div class="scroll q-pt-sm" style="height: 40vh; max-height: 40vh">
            <draggable class="q-list" handle=".handle" ghost-class="ghost" v-model="state.actions" item-key="index">
              <template v-slot:item="{ index, element }">
                <q-item>
                  <q-item-section avatar>
                    <q-icon class="handle" style="cursor: move" name="drag_handle" />
                  </q-item-section>
                  <q-item-section v-if="element.type === 'script'">
                    <q-item-label>
                      <q-icon size="sm" name="description" color="primary" /> &nbsp; {{ element.name }}
                    </q-item-label>
                    <q-item-label caption> Arguments: {{ element.script_args }} </q-item-label>
                    <q-item-label caption> Timeout: {{ element.timeout }} </q-item-label>
                  </q-item-section>
                  <q-item-section v-else>
                    <q-item-label>
                      <q-icon size="sm" name="terminal" color="primary" /> &nbsp;
                      <q-icon
                        size="sm"
                        :name="element.shell === 'cmd' ? 'mdi-microsoft-windows' : 'mdi-powershell'"
                        color="primary"
                      />
                      {{ element.command }}
                    </q-item-label>
                    <q-item-label caption> Timeout: {{ element.timeout }} </q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-icon class="cursor-pointer" color="negative" name="close" @click="removeAction(index)" />
                  </q-item-section>
                </q-item>
              </template>
            </draggable>
          </div>
        </q-step>

        <q-step :name="3" title="Choose Schedule" :error="!isValidStep3">
          <div class="scroll" style="height: 60vh; max-height: 60vh">
            <q-form @submit.prevent ref="taskDetailForm">
              <q-card-section>
                <q-option-group
                  v-model="state.task_type"
                  label="Task run type"
                  :options="taskTypeOptions"
                  dense
                  inline
                  @update:model-value="$refs.taskDetailForm.resetValidation()"
                />
              </q-card-section>

              <!-- task start/expire time fields -->
              <q-card-section v-if="['runonce', 'daily', 'weekly', 'monthly'].includes(state.task_type)" class="row">
                <!-- start time input -->
                <q-input
                  class="col-6 q-pa-sm"
                  type="datetime-local"
                  dense
                  label="Start time"
                  stack-label
                  filled
                  v-model="state.run_time_date"
                  hint="Agent timezone will be used"
                  :rules="[val => !!val || '*Required']"
                />

                <!-- expires on input -->
                <q-input
                  class="col-6 q-pa-sm"
                  type="datetime-local"
                  dense
                  stack-label
                  label="Expires on"
                  filled
                  v-model="state.expire_date"
                  hint="Agent timezone will be used"
                />
              </q-card-section>

              <!-- daily options -->
              <q-card-section v-if="state.task_type === 'daily'" class="row">
                <!-- daily interval -->
                <q-input
                  :rules="[
                    val => !!val || '*Required',
                    val => (val > 0 && val < 256) || 'Daily interval must be greater than 0 and less than 3',
                  ]"
                  dense
                  type="number"
                  label="Run every"
                  v-model.number="state.daily_interval"
                  filled
                  class="col-6 q-pa-sm"
                >
                  <template v-slot:append>
                    <span class="text-subtitle2">days</span>
                  </template>
                </q-input>
                <div class="col-6 q-pa-sm"></div>
              </q-card-section>

              <!-- weekly options -->
              <q-card-section v-if="state.task_type === 'weekly'" class="row">
                <!-- weekly interval -->
                <q-input
                  :rules="[
                    val => !!val || '*Required',
                    val => (val > 0 && val < 53) || 'Weekly interval must be greater than 0 and less than 3',
                  ]"
                  class="col-6 q-pa-sm"
                  dense
                  label="Run every"
                  v-model="state.weekly_interval"
                  filled
                >
                  <template v-slot:append>
                    <span class="text-subtitle2">weeks</span>
                  </template>
                </q-input>

                <div class="col-6 q-pa-sm"></div>

                <div class="col-12 q-pa-sm">
                  <!-- day of week input -->
                  Run on Days:
                  <q-option-group
                    :rules="[val => val.length > 0 || '*Required']"
                    inline
                    dense
                    :options="dayOfWeekOptions"
                    type="checkbox"
                    v-model="state.run_time_bit_weekdays"
                  />
                </div>
              </q-card-section>

              <!-- monthly options -->
              <q-card-section v-if="state.task_type === 'monthly'" class="row">
                <!-- type of monthly schedule -->
                <q-option-group
                  class="col-12 q-pa-sm"
                  v-model="monthlyType"
                  inline
                  :options="[
                    { label: 'On Days', value: 'days' },
                    { label: 'On Weeks', value: 'weeks' },
                  ]"
                />

                <!-- month select input -->
                <q-select
                  :rules="[val => val.length > 0 || '*Required']"
                  class="col-4 q-pa-sm"
                  filled
                  dense
                  options-dense
                  v-model="state.monthly_months_of_year"
                  :options="monthOptions"
                  label="Run on Months"
                  multiple
                  emit-value
                  map-options
                >
                  <template v-slot:before-options>
                    <q-item>
                      <q-item-section>
                        <q-item-label>All months</q-item-label>
                      </q-item-section>
                      <q-item-section side>
                        <q-checkbox dense v-model="allMonthsCheckbox" @update:model-value="toggleMonths" />
                      </q-item-section>
                    </q-item>
                  </template>

                  <template v-slot:option="{ itemProps, opt, selected, toggleOption }">
                    <q-item v-bind="itemProps">
                      <q-item-section>
                        <q-item-label v-html="opt.label" />
                      </q-item-section>
                      <q-item-section side>
                        <q-checkbox
                          dense
                          :model-value="selected"
                          @update:model-value="
                            toggleOption(opt);
                            allMonthsCheckbox = false;
                          "
                        />
                      </q-item-section>
                    </q-item>
                  </template>
                </q-select>

                <!-- days of month select input -->
                <q-select
                  v-if="monthlyType === 'days'"
                  :rules="[val => val.length > 0 || '*Required']"
                  class="col-4 q-pa-sm"
                  filled
                  dense
                  options-dense
                  v-model="state.monthly_days_of_month"
                  :options="dayOfMonthOptions"
                  label="Run on Days"
                  multiple
                  emit-value
                  map-options
                >
                  <template v-slot:before-options>
                    <q-item>
                      <q-item-section>
                        <q-item-label>All days</q-item-label>
                      </q-item-section>
                      <q-item-section side>
                        <q-checkbox dense v-model="allMonthDaysCheckbox" @update:model-value="toggleMonthDays" />
                      </q-item-section>
                    </q-item>
                  </template>

                  <template v-slot:option="{ itemProps, opt, selected, toggleOption }">
                    <q-item v-bind="itemProps">
                      <q-item-section>
                        <q-item-label v-html="opt.label" />
                      </q-item-section>
                      <q-item-section side>
                        <q-checkbox
                          dense
                          :model-value="selected"
                          @update:model-value="
                            toggleOption(opt);
                            allMonthDaysCheckbox = false;
                          "
                        />
                      </q-item-section>
                    </q-item>
                  </template>
                </q-select>

                <div v-if="monthlyType === 'days'" class="col-4"></div>

                <!-- week of month select input -->
                <q-select
                  v-if="monthlyType === 'weeks'"
                  :rules="[val => val.length > 0 || '*Required']"
                  class="col-4 q-pa-sm"
                  filled
                  dense
                  options-dense
                  v-model="state.monthly_weeks_of_month"
                  :options="weekOptions"
                  label="Run on weeks"
                  multiple
                  emit-value
                  map-options
                >
                  <template v-slot:option="{ itemProps, opt, selected, toggleOption }">
                    <q-item v-bind="itemProps">
                      <q-item-section>
                        <q-item-label v-html="opt.label" />
                      </q-item-section>
                      <q-item-section side>
                        <q-checkbox dense :model-value="selected" @update:model-value="toggleOption(opt)" />
                      </q-item-section>
                    </q-item>
                  </template>
                </q-select>

                <!-- day of week select input -->
                <q-select
                  v-if="monthlyType === 'weeks'"
                  :rules="[val => val.length > 0 || '*Required']"
                  class="col-4 q-pa-sm"
                  filled
                  dense
                  options-dense
                  v-model="state.run_time_bit_weekdays"
                  :options="dayOfWeekOptions"
                  label="Run on days"
                  multiple
                  emit-value
                  map-options
                >
                  <template v-slot:before-options>
                    <q-item>
                      <q-item-section>
                        <q-item-label>All days</q-item-label>
                      </q-item-section>
                      <q-item-section side>
                        <q-checkbox dense v-model="allWeekDaysCheckbox" @update:model-value="toggleWeekDays" />
                      </q-item-section>
                    </q-item>
                  </template>

                  <template v-slot:option="{ itemProps, opt, selected, toggleOption }">
                    <q-item v-bind="itemProps">
                      <q-item-section>
                        <q-item-label v-html="opt.label" />
                      </q-item-section>
                      <q-item-section side>
                        <q-checkbox
                          dense
                          :model-value="selected"
                          @update:model-value="
                            toggleOption(opt);
                            allWeekDaysCheckbox = false;
                          "
                        />
                      </q-item-section>
                    </q-item>
                  </template>
                </q-select>
              </q-card-section>

              <q-card-section v-if="state.task_type !== 'checkfailure' && state.task_type !== 'manual'" class="row">
                <div class="col-12 text-h6">Advanced Settings</div>
                <q-input
                  class="col-6 q-pa-sm"
                  dense
                  label="Repeat task every"
                  filled
                  v-model="state.task_repetition_interval"
                  placeholder="e.g. 30m (30 minutes) or 1h (1 hour)"
                  lazy-rules
                  :rules="[
                    val =>
                      !val || validateTimePeriod(val) || 'Valid values are 1-3 digits followed by (D|d|H|h|M|m|S|s)',
                  ]"
                />

                <q-input
                  :disable="!state.task_repetition_interval"
                  class="col-6 q-pa-sm"
                  dense
                  label="Task repeat duration"
                  filled
                  v-model="state.task_repetition_duration"
                  placeholder="e.g. 6h (6 hours) or 1d (1 day)"
                  lazy-rules
                  :rules="[
                    val => validateTimePeriod(val) || 'Valid values are 1-3 digits followed by (D|d|H|h|M|m|S|s)',
                    val => (state.task_repetition_interval ? !!val : true), // field is required if repetition interval is set
                    val =>
                      convertPeriodToSeconds(val) >= convertPeriodToSeconds(state.task_repetition_interval) ||
                      'Repetition duration must be greater than repetition interval',
                  ]"
                />

                <q-checkbox
                  :disable="!state.task_repetition_interval"
                  class="col-6 q-pa-sm"
                  dense
                  v-model="state.stop_task_at_duration_end"
                  label="Stop all tasks at the end of duration"
                />
                <div class="col-6"></div>

                <q-input
                  class="col-6 q-pa-sm"
                  dense
                  label="Random task delay"
                  filled
                  v-model="state.random_task_delay"
                  placeholder="e.g. 2m (2 minutes) or 1h (1 hour)"
                  lazy-rules
                  :rules="[
                    val =>
                      !val || validateTimePeriod(val) || 'Valid values are 1-3 digits followed by (D|d|H|h|M|m|S|s)',
                  ]"
                />
                <div class="col-6"></div>
                <q-checkbox
                  :disable="!state.expire_date"
                  class="col-6 q-pa-sm"
                  dense
                  v-model="state.remove_if_not_scheduled"
                  label="Delete task if not scheduled for 30 days"
                >
                  <q-tooltip>Must set an expire date</q-tooltip>
                </q-checkbox>
                <div class="col-6"></div>
                <q-checkbox
                  :disable="state.task_type === 'runonce'"
                  class="col-6 q-pa-sm"
                  dense
                  v-model="state.run_asap_after_missed"
                  label="Run task ASAP after a scheduled start is missed"
                />

                <div class="col-6"></div>

                <tactical-dropdown
                  class="col-6 q-pa-sm"
                  label="Task instance policy"
                  :options="taskInstancePolicyOptions"
                  v-model="state.task_instance_policy"
                  filled
                  mapOptions
                />
              </q-card-section>

              <!-- check failure options -->
              <q-card-section v-else-if="state.task_type === 'checkfailure'" class="row">
                <tactical-dropdown
                  class="col-6 q-pa-sm"
                  :rules="[val => !!val || '*Required']"
                  v-model="state.assigned_check"
                  filled
                  :options="checkOptions"
                  label="Select Check"
                  mapOptions
                />
              </q-card-section>
            </q-form>
          </div>
        </q-step>
      </q-stepper>
      <q-card-actions align="right">
        <q-btn flat label="Cancel" v-close-popup />
        <q-btn v-if="step > 1" label="Back" @click="$refs.stepper.previous()" color="primary" flat />
        <q-btn
          v-if="step < 3"
          @click="validateStep(step === 1 ? $refs.taskGeneralForm : undefined, $refs.stepper)"
          color="primary"
          label="Next"
          flat
        />
        <q-btn
          v-else
          :label="task ? 'Edit Task' : 'Add Task'"
          color="primary"
          @click="validateStep($refs.taskDetailForm, $refs.stepper)"
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
import { ref, watch, onMounted } from "vue";
import { useDialogPluginComponent, date } from "quasar";
import draggable from "vuedraggable";
import { saveTask, updateTask } from "@/api/tasks";
import { useScriptDropdown } from "@/composables/scripts";
import { useCheckDropdown } from "@/composables/checks";
import { useCustomFieldDropdown } from "@/composables/core";
import { notifySuccess, notifyError } from "@/utils/notify";
import { validateTimePeriod } from "@/utils/validation";
import { convertPeriodToSeconds, convertToBitArray, convertFromBitArray, formatDateInputField } from "@/utils/format";

// ui imports
import TacticalDropdown from "@/components/ui/TacticalDropdown.vue";

// static data
const severityOptions = [
  { label: "Informational", value: "info" },
  { label: "Warning", value: "warning" },
  { label: "Error", value: "error" },
];

const taskTypeOptions = [
  { label: "Daily", value: "daily" },
  { label: "Weekly", value: "weekly" },
  { label: "Monthly", value: "monthly" },
  { label: "Run Once", value: "runonce" },
  { label: "On check failure", value: "checkfailure" },
  { label: "Manual", value: "manual" },
];

const dayOfWeekOptions = [
  { label: "Monday", value: 0x2 },
  { label: "Tuesday", value: 0x4 },
  { label: "Wednesday", value: 0x8 },
  { label: "Thursday", value: 0x10 },
  { label: "Friday", value: 0x20 },
  { label: "Saturday", value: 0x40 },
  { label: "Sunday", value: 0x1 },
];

const dayOfMonthOptions = (() => {
  let result = [];
  let day = 0x1;
  for (let i = 1; i <= 31; i++) {
    result.push({ label: `${i}`, value: day });
    day = day << 1;
  }
  result.push({ label: "Last Day", value: 0x80000000 });
  return result;
})();

const monthOptions = [
  { label: "January", value: 0x1 },
  { label: "February", value: 0x2 },
  { label: "March", value: 0x4 },
  { label: "April", value: 0x8 },
  { label: "May", value: 0x10 },
  { label: "June", value: 0x20 },
  { label: "July", value: 0x40 },
  { label: "August", value: 0x80 },
  { label: "September", value: 0x100 },
  { label: "October", value: 0x200 },
  { label: "November", value: 0x400 },
  { label: "December", value: 0x800 },
];

const weekOptions = [
  { label: "First Week", value: 0x1 },
  { label: "Second Week", value: 0x2 },
  { label: "Third Week", value: 0x4 },
  { label: "Fourth Week", value: 0x8 },
  { label: "Last Week", value: 0x10 },
];

const taskInstancePolicyOptions = [
  { label: "Run in Parallel", value: 0 },
  { label: "Queue Task", value: 1 },
  { label: "Ignore", value: 2 },
  { label: "Stop Existing", value: 3 },
];

export default {
  components: { TacticalDropdown, draggable },
  name: "AddAutomatedTask",
  emits: [...useDialogPluginComponent.emits],
  props: {
    parent: Object, // parent policy or agent for task
    task: Object, // only for editing
  },
  setup(props) {
    // setup quasar dialog
    const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();

    // setup dropdowns
    const { script, scriptOptions, defaultTimeout, defaultArgs } = useScriptDropdown(undefined, {
      onMount: true,
    });

    // set defaultTimeout to 30
    defaultTimeout.value = 30;

    const { checkOptions, getCheckOptions } = useCheckDropdown();
    const { customFieldOptions } = useCustomFieldDropdown({ onMount: true });

    // add task logic
    const task = props.task
      ? ref(Object.assign({}, props.task))
      : ref({
          ...props.parent,
          actions: [],
          assigned_check: null,
          custom_field: null,
          name: null,
          expire_date: null,
          run_time_date: formatDateInputField(Date.now()),
          run_time_bit_weekdays: [],
          weekly_interval: 1,
          daily_interval: 1,
          monthly_months_of_year: [],
          monthly_days_of_month: [],
          monthly_weeks_of_month: [],
          task_instance_policy: 0,
          task_repetition_interval: null,
          task_repetition_duration: null,
          stop_task_at_duration_end: false,
          random_task_delay: null,
          remove_if_not_scheduled: false,
          run_asap_after_missed: true,
          task_type: "daily",
          alert_severity: "info",
          collector_all_output: false,
          continue_on_error: true,
        });

    const actionType = ref("script");
    const command = ref("");
    const shell = ref("cmd");
    const monthlyType = ref("days");
    const collector = ref(false);
    const loading = ref(false);

    // before-options check boxes that will select all options

    // if all months is selected or cleared it will either clear the monthly_months_of_year array or add all options to it.
    const allMonthsCheckbox = ref(false);
    function toggleMonths() {
      task.value.monthly_months_of_year = allMonthsCheckbox.value ? monthOptions.map(month => month.value) : [];
    }

    const allMonthDaysCheckbox = ref(false);
    function toggleMonthDays() {
      task.value.monthly_days_of_month = allMonthDaysCheckbox.value ? dayOfMonthOptions.map(day => day.value) : [];
    }

    const allWeekDaysCheckbox = ref(false);
    function toggleWeekDays() {
      task.value.run_time_bit_weekdays = allWeekDaysCheckbox.value ? dayOfWeekOptions.map(day => day.value) : [];
    }

    // function for adding script and commands to be run from task
    function addAction() {
      if (actionType.value === "script" && (!script.value || !defaultTimeout.value)) {
        notifyError("Script and timeout must be set");
        return;
      } else if (actionType.value === "cmd" && (!command.value || !defaultTimeout.value)) {
        notifyError("A command and timeout must be set");
        return;
      }

      if (actionType.value === "script") {
        task.value.actions.push({
          type: "script",
          name: scriptOptions.value.find(option => option.value === script.value).label,
          script: script.value,
          timeout: defaultTimeout.value,
          script_args: defaultArgs.value,
        });
      } else if (actionType.value === "cmd") {
        task.value.actions.push({
          type: "cmd",
          command: command.value,
          shell: shell.value,
          timeout: defaultTimeout.value,
        });
      }

      // clear fields after add
      script.value = null;
      defaultArgs.value = [];
      defaultTimeout.value = 30;
      command.value = "";
    }

    function removeAction(index) {
      task.value.actions.splice(index, 1);
    }

    // runs whenever task data is saved
    function processTaskDataforDB(taskData) {
      // copy data
      let data = Object.assign({}, taskData);

      // converts fields from arrays to integers
      data.run_time_bit_weekdays =
        taskData.run_time_bit_weekdays.length > 0 ? convertFromBitArray(taskData.run_time_bit_weekdays) : null;

      data.monthly_months_of_year =
        taskData.monthly_months_of_year.length > 0 ? convertFromBitArray(taskData.monthly_months_of_year) : null;

      data.monthly_days_of_month =
        taskData.monthly_days_of_month.length > 0 ? convertFromBitArray(taskData.monthly_days_of_month) : null;

      data.monthly_weeks_of_month =
        taskData.monthly_weeks_of_month.length > 0 ? convertFromBitArray(taskData.monthly_weeks_of_month) : null;

      // Add Z back to run_time_date and expires_date
      data.run_time_date += "Z";

      if (taskData.expire_date) data.expire_date += "Z";

      // change task type if monthly day of week is set
      if (task.value.task_type === "monthly" && monthlyType.value === "weeks") {
        data.task_type = "monthlydow";
      }

      return data;
    }

    // runs when editing a task to convert values to be compatible with quasar
    function processTaskDatafromDB() {
      // converts fields from integers to arrays
      task.value.run_time_bit_weekdays = task.value.run_time_bit_weekdays
        ? convertToBitArray(task.value.run_time_bit_weekdays)
        : [];
      task.value.monthly_months_of_year = task.value.monthly_months_of_year
        ? convertToBitArray(task.value.monthly_months_of_year)
        : [];
      task.value.monthly_days_of_month = task.value.monthly_days_of_month
        ? convertToBitArray(task.value.monthly_days_of_month)
        : [];
      task.value.monthly_weeks_of_month = task.value.monthly_weeks_of_month
        ? convertToBitArray(task.value.monthly_weeks_of_month)
        : [];

      // remove milliseconds and Z to work with native date input
      task.value.run_time_date = formatDateInputField(task.value.run_time_date);

      if (task.value.expire_date) task.value.expire_date = formatDateInputField(task.value.expire_date);

      // set task type if monthlydow is being used
      if (task.value.task_type === "monthlydow") {
        task.value.task_type = "monthly";
        monthlyType.value = "weeks";
      }
    }

    async function submit() {
      loading.value = true;
      try {
        const result = props.task
          ? await updateTask(task.value.id, processTaskDataforDB(task.value))
          : await saveTask(processTaskDataforDB(task.value));
        notifySuccess(result);
        onDialogOK();
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    // format task data to match what quasar expects if editing
    if (props.task) processTaskDatafromDB();

    watch(
      () => task.value.task_type,
      (newValue, oldValue) => {
        task.value.assigned_check = null;
        task.value.run_time_bit_weekdays = [];
        task.value.remove_if_not_scheduled = false;
        task.value.task_repetition_interval = null;
        task.value.task_repetition_duration = null;
        task.value.stop_task_at_duration_end = false;
        task.value.random_task_delay = null;
        task.value.weekly_interval = 1;
        task.value.daily_interval = 1;
        task.value.monthly_months_of_year = [];
        task.value.monthly_days_of_month = [];
        task.value.monthly_weeks_of_month = [];
        task.value.task_instance_policy = 0;
        task.value.expire_date = null;
      }
    );

    // check the collector box when editing task and custom field is set
    if (props.task && props.task.custom_field) collector.value = true;

    // stepper logic
    const step = ref(1);
    const isValidStep1 = ref(true);
    const isValidStep2 = ref(true);
    const isValidStep3 = ref(true);

    function validateStep(form, stepper) {
      if (step.value === 2) {
        if (task.value.actions.length > 0) {
          isValidStep2.value = true;
          stepper.next();
          return;
        } else {
          notifyError("There must be at least one action");
        }

        // steps 1 or 3
      } else {
        form.validate().then(result => {
          if (step.value === 1) {
            isValidStep1.value = result;
            if (result) stepper.next();
          } else if (step.value === 3) {
            isValidStep3.value = result;
            if (result) submit();
          }
        });
      }
    }

    onMounted(() => {
      getCheckOptions(props.parent);
    });

    return {
      // reactive data
      state: task,
      script,
      defaultTimeout,
      defaultArgs,
      actionType,
      command,
      shell,
      allMonthsCheckbox,
      allMonthDaysCheckbox,
      allWeekDaysCheckbox,
      collector,
      monthlyType,
      loading,
      step,
      isValidStep1,
      isValidStep2,
      isValidStep3,
      scriptOptions,
      checkOptions,
      customFieldOptions,

      // non-reactive data
      validateTimePeriod,
      convertPeriodToSeconds,
      severityOptions,
      dayOfWeekOptions,
      dayOfMonthOptions,
      weekOptions,
      monthOptions,
      taskTypeOptions,
      taskInstancePolicyOptions,

      // methods
      submit,
      validateStep,
      addAction,
      removeAction,
      toggleMonths,
      toggleMonthDays,
      toggleWeekDays,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>

<style scoped>
.ghost {
  opacity: 0.5;
}
</style>
