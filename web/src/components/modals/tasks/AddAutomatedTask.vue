<template>
  <q-card class="q-pa-xs" style="min-width: 40vw">
    <q-card-section class="row items-center">
      <div class="text-h6">Add Automated Task</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-card-section v-if="scriptOptions.length === 0">
      <p>You need to upload a script first</p>
      <p>Settings -> Script Manager</p>
    </q-card-section>
    <q-stepper v-else v-model="step" ref="stepper" color="primary" animated>
      <q-step :name="1" title="Select Task" :done="step1Done" :error="!step1Done">
        <q-card-section>
          <q-select
            :rules="[val => !!val || '*Required']"
            dense
            options-dense
            outlined
            v-model="autotask.script"
            :options="scriptOptions"
            label="Select script"
            map-options
            emit-value
            @update:model-value="setScriptDefaults"
          >
            <template v-slot:option="scope">
              <q-item v-if="!scope.opt.category" v-bind="scope.itemProps" class="q-pl-lg">
                <q-item-section>
                  <q-item-label v-html="scope.opt.label"></q-item-label>
                </q-item-section>
              </q-item>
              <q-item-label v-if="scope.opt.category" v-bind="scope.itemProps" header class="q-pa-sm">{{
                scope.opt.category
              }}</q-item-label>
            </template>
          </q-select>
        </q-card-section>
        <q-card-section>
          <q-select
            dense
            label="Script Arguments (press Enter after typing each argument)"
            filled
            v-model="autotask.script_args"
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
            v-model="autotask.name"
            label="Descriptive name of task"
            class="q-pb-none"
          />
        </q-card-section>
        <q-card-section>
          <q-checkbox
            dense
            label="Collector Task"
            v-model="collector"
            class="q-pb-sm"
            @update:model-value="
              () => {
                autotask.custom_field = null;
                autotask.collector_all_ouput = false;
              }
            "
          />
          <q-select
            v-if="collector"
            v-model="autotask.custom_field"
            :options="customFieldOptions"
            dense
            label="Custom Field to update"
            outlined
            map-options
            emit-value
            options-dense
            hint="The last line of script output will be saved to custom field selected"
          />
          <q-checkbox
            v-if="collector"
            dense
            label="Save all output (Only for text area)"
            v-model="autotask.collector_all_output"
            class="q-py-sm"
          />
        </q-card-section>
        <q-card-section>
          <q-select
            v-model="autotask.alert_severity"
            :options="severityOptions"
            dense
            label="Alert Severity"
            outlined
            map-options
            emit-value
            options-dense
          />
        </q-card-section>
        <q-card-section>
          <q-input
            :rules="[val => !!val || '*Required']"
            outlined
            dense
            v-model.number="autotask.timeout"
            type="number"
            label="Maximum permitted execution time (seconds)"
            class="q-pb-none"
          />
        </q-card-section>
      </q-step>

      <q-step :name="2" title="Choose Schedule" :done="step2Done" :error="!step2Done">
        <q-radio v-model="autotask.task_type" val="scheduled" label="Scheduled" @update:model-value="clear" />
        <q-radio v-model="autotask.task_type" val="runonce" label="Run Once" @update:model-value="clear" />
        <q-radio v-model="autotask.task_type" val="checkfailure" label="On check failure" @update:model-value="clear" />
        <q-radio v-model="autotask.task_type" val="manual" label="Manual" @update:model-value="clear" />
        <div v-if="autotask.task_type === 'scheduled'" class="row q-pa-lg">
          <div class="col-3">
            Run on Days:
            <q-option-group :options="dayOptions" label="Days" type="checkbox" v-model="autotask.run_time_days" />
          </div>
          <div class="col-2"></div>
          <div class="col-6">
            At time:
            <q-time v-model="autotask.run_time_minute" />
          </div>
          <div class="col-1"></div>
        </div>
        <div v-if="autotask.task_type === 'runonce'" class="row q-pa-lg">
          <div class="col-11">
            <q-input filled v-model="autotask.run_time_date" hint="Agent timezone will be used">
              <template v-slot:append>
                <q-icon name="event" class="cursor-pointer">
                  <q-popup-proxy transition-show="scale" transition-hide="scale">
                    <q-date v-model="autotask.run_time_date" mask="YYYY-MM-DD HH:mm">
                      <div class="row items-center justify-end">
                        <q-btn v-close-popup label="Close" color="primary" flat />
                      </div>
                    </q-date>
                  </q-popup-proxy>
                </q-icon>
                <q-icon name="access_time" class="cursor-pointer">
                  <q-popup-proxy transition-show="scale" transition-hide="scale">
                    <q-time v-model="autotask.run_time_date" mask="YYYY-MM-DD HH:mm">
                      <div class="row items-center justify-end">
                        <q-btn v-close-popup label="Close" color="primary" flat />
                      </div>
                    </q-time>
                  </q-popup-proxy>
                </q-icon>
              </template>
            </q-input>
            <div class="q-gutter-sm">
              <q-checkbox v-model="autotask.remove_if_not_scheduled" label="Delete task after scheduled date" />
            </div>
            <div class="q-gutter-sm">
              <q-checkbox
                v-model="autotask.run_asap_after_missed"
                label="Run task ASAP after a scheduled start is missed (requires agent v1.4.7)"
              />
            </div>
          </div>
          <div class="col-1"></div>
        </div>
        <div v-else-if="autotask.task_type === 'checkfailure'" class="q-pa-lg">
          When Check Fails:
          <q-select
            :rules="[val => !!val || '*Required']"
            dense
            options-dense
            outlined
            v-model="autotask.assigned_check"
            :options="checksOptions"
            label="Select Check"
            map-options
            emit-value
          />
        </div>
      </q-step>

      <template v-slot:navigation>
        <q-stepper-navigation>
          <q-btn
            v-if="step === 2"
            :disable="!step1Done || !step2Done"
            color="primary"
            @click="addTask"
            label="Add Task"
          />
          <q-btn v-else @click="step2" color="primary" label="Next" />
          <q-btn v-if="step > 1" flat color="primary" @click="$refs.stepper.previous()" label="Back" class="q-ml-sm" />
        </q-stepper-navigation>
      </template>
    </q-stepper>
  </q-card>
</template>

<script>
import { mapGetters } from "vuex";
import mixins from "@/mixins/mixins";

export default {
  name: "AddAutomatedTask",
  emits: ["close"],
  props: {
    policypk: Number,
  },
  mixins: [mixins],
  data() {
    return {
      step: 1,
      scriptOptions: [],
      customFieldOptions: [],
      collector: false,
      autotask: {
        script: null,
        script_args: [],
        assigned_check: null,
        custom_field: null,
        name: null,
        run_time_days: [],
        run_time_minute: null,
        run_time_date: null,
        remove_if_not_scheduled: false,
        run_asap_after_missed: true,
        task_type: "scheduled",
        timeout: 120,
        alert_severity: "info",
        collector_all_output: false,
      },
      policyChecks: [],
      severityOptions: [
        { label: "Informational", value: "info" },
        { label: "Warning", value: "warning" },
        { label: "Error", value: "error" },
      ],
      dayOptions: [
        { label: "Monday", value: "Monday" },
        { label: "Tuesday", value: "Tuesday" },
        { label: "Wednesday", value: "Wednesday" },
        { label: "Thursday", value: "Thursday" },
        { label: "Friday", value: "Friday" },
        { label: "Saturday", value: "Saturday" },
        { label: "Sunday", value: "Sunday" },
      ],
    };
  },
  methods: {
    setScriptDefaults() {
      const script = this.scriptOptions.find(i => i.value === this.autotask.script);

      this.autotask.timeout = script.timeout;
      this.autotask.script_args = script.args;
    },
    clear() {
      this.autotask.assigned_check = null;
      this.autotask.run_time_days = [];
      this.autotask.run_time_minute = null;
      this.autotask.run_time_date = null;
      this.autotask.remove_if_not_scheduled = false;
    },
    addTask() {
      if (!this.step1Done || !this.step2Done) {
        this.notifyError("Some steps incomplete");
      } else {
        const pk = this.policypk ? { policy: this.policypk } : { agent: this.selectedAgentPk };

        const data = {
          ...pk,
          autotask: this.autotask,
        };

        this.$axios
          .post("tasks/automatedtasks/", data)
          .then(r => {
            this.$emit("close");

            if (!this.policypk) {
              this.$store.dispatch("loadAutomatedTasks", this.selectedAgentPk);
              this.$store.dispatch("loadChecks", this.selectedAgentPk);
            }
            this.notifySuccess(r.data);
          })
          .catch(e => {});
      }
    },
    getPolicyChecks() {
      this.$axios
        .get(`/automation/${this.policypk}/policychecks/`)
        .then(r => {
          this.policyChecks = r.data;
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    step2() {
      if (this.step1Done) {
        this.$refs.stepper.next();
      } else {
        if (!this.autotask.script) this.notifyError("Script field is required");
        else if (!this.autotask.name) this.notifyError("Name field is required");
        else if (!this.autotask.timeout) this.notifyError("Timeout field is required");
      }
    },
  },
  computed: {
    ...mapGetters(["selectedAgentPk", "showCommunityScripts"]),
    checks() {
      return this.policypk
        ? this.policyChecks
        : this.$store.state.agentChecks.filter(check => check.managed_by_policy === false);
    },
    checksOptions() {
      const r = [];
      this.checks.forEach(i => {
        r.push({ label: i.readable_desc, value: i.id });
      });
      return r.sort((a, b) => a.label.localeCompare(b.label));
    },
    step1Done() {
      return !!this.autotask.script && !!this.autotask.name && !!this.autotask.timeout ? true : false;
    },
    step2Done() {
      if (this.autotask.task_type === "scheduled") {
        return this.autotask.run_time_days.length !== 0 && this.autotask.run_time_minute !== null ? true : false;
      } else if (this.autotask.task_type === "checkfailure") {
        return this.autotask.assigned_check !== null ? true : false;
      } else if (this.autotask.task_type === "manual") {
        return true;
      } else if (this.autotask.task_type === "runonce") {
        return this.autotask.run_time_date !== null ? true : false;
      } else {
        return false;
      }
    },
  },
  mounted() {
    this.getScriptOptions(this.showCommunityScripts).then(options => (this.scriptOptions = Object.freeze(options)));

    if (this.policypk) {
      this.getPolicyChecks();
    }

    this.getCustomFields("agent").then(r => {
      this.customFieldOptions = r.data.map(field => ({ label: field.name, value: field.id }));
    });
  },
};
</script>