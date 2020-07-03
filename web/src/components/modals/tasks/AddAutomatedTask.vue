<template>
  <q-card v-if="scripts.length === 0" class="q-pa-xs" style="min-width: 400px">
    <q-card-section class="row items-center">
      <div class="text-h6">Add Automated Task</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>
    <q-card-section>
      <p>You need to upload a script first</p>
      <p>Settings -> Script Manager</p>
    </q-card-section>
  </q-card>
  <q-card v-else class="q-pa-xs" style="min-width: 550px">
    <q-card-section class="row items-center">
      <div class="text-h6">Add Automated Task</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>
    <q-stepper v-model="step" ref="stepper" color="primary" animated>
      <q-step :name="1" title="Select Task" :done="step1Done" :error="!step1Done">
        <q-card-section>
          <q-select
            :rules="[val => !!val || '*Required']"
            dense
            outlined
            v-model="autotask.script"
            :options="scriptOptions"
            label="Select task"
            map-options
            emit-value
          />
        </q-card-section>
        <q-card-section>
          <q-input
            :rules="[val => !!val || '*Required']"
            outlined
            dense
            v-model="autotask.name"
            label="Descriptive name of task"
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
          />
        </q-card-section>
      </q-step>

      <q-step :name="2" title="Choose Schedule" :done="step2Done" :error="!step2Done">
        <q-radio v-model="autotask.task_type" val="scheduled" label="Scheduled" @input="clear" />
        <q-radio
          v-model="autotask.task_type"
          val="checkfailure"
          label="On check failure"
          @input="clear"
        />
        <q-radio v-model="autotask.task_type" val="manual" label="Manual" @input="clear" />
        <div v-if="autotask.task_type === 'scheduled'" class="row q-pa-lg">
          <div class="col-3">
            Run on Days:
            <q-option-group
              :options="dayOptions"
              label="Days"
              type="checkbox"
              v-model="autotask.run_time_days"
            />
          </div>
          <div class="col-2"></div>
          <div class="col-6">
            At time:
            <q-time v-model="autotask.run_time_minute" />
          </div>
          <div class="col-1"></div>
        </div>
        <div v-else-if="autotask.task_type === 'checkfailure'" class="q-pa-lg">
          When Check Fails:
          <q-select
            :rules="[val => !!val || '*Required']"
            dense
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
          <q-btn v-else @click="$refs.stepper.next()" color="primary" label="Next" />
          <q-btn
            v-if="step > 1"
            flat
            color="primary"
            @click="$refs.stepper.previous()"
            label="Back"
            class="q-ml-sm"
          />
        </q-stepper-navigation>
      </template>
    </q-stepper>
  </q-card>
</template>

<script>
import axios from "axios";
import { mapState, mapGetters } from "vuex";
import mixins from "@/mixins/mixins";

export default {
  name: "AddAutomatedTask",
  props: {
    policypk: Number
  },
  mixins: [mixins],
  data() {
    return {
      step: 1,
      autotask: {
        script: null,
        assigned_check: null,
        name: null,
        run_time_days: [],
        run_time_minute: null,
        task_type: "scheduled",
        timeout: 120
      },
      dayOptions: [
        { label: "Monday", value: 0 },
        { label: "Tuesday", value: 1 },
        { label: "Wednesday", value: 2 },
        { label: "Thursday", value: 3 },
        { label: "Friday", value: 4 },
        { label: "Saturday", value: 5 },
        { label: "Sunday", value: 6 }
      ]
    };
  },
  methods: {
    clear() {
      this.autotask.assigned_check = null;
      this.autotask.run_time_days = [];
      this.autotask.run_time_minute = null;
    },
    addTask() {
      if (!this.step1Done || !this.step2Done) {
        this.notifyError("Some steps incomplete");
      } else {
        const pk = this.policypk ? { policy: this.policypk } : { agent: this.selectedAgentPk };

        const data = {
          ...pk,
          autotask: this.autotask
        };

        axios
          .post("tasks/automatedtasks/", data)
          .then(r => {
            this.$emit("close");

            if (!this.policypk) {
              this.$store.dispatch("loadAutomatedTasks", this.selectedAgentPk);
              this.$store.dispatch("loadChecks", this.selectedAgentPk);
            } else {
              this.$store.dispatch("automation/loadPolicyAutomatedTasks", this.policypk);
              this.$store.dispatch("automation/loadPolicyChecks", this.policypk);
            }
            this.notifySuccess(r.data);
          })
          .catch(e => this.notifyError(e.response.data));
      }
    },
    getScripts() {
      this.$store.dispatch("getScripts");
    }
  },
  computed: {
    ...mapGetters(["selectedAgentPk", "scripts"]),
    checks() {
      return this.policypk ? this.$store.state.automation.checks : this.$store.state.agentChecks.filter(
          check => check.managed_by_policy === false
        );
    },
    checksOptions() {
      const r = [];
      this.checks.forEach(i => {
        r.push({ label: i.readable_desc, value: i.id });
      });
      return r;
    },
    scriptOptions() {
      const r = [];
      this.scripts.forEach(i => {
        r.push({ label: i.name, value: i.id });
      });
      return r;
    },
    step1Done() {
      return this.step > 1 && this.autotask.script !== null && this.autotask.name && this.autotask.timeout
        ? true
        : false;
    },
    step2Done() {
      if (this.autotask.task_type === "scheduled") {
        return this.autotask.run_time_days.length !== 0 && this.autotask.run_time_minute !== null ? true : false;
      } else if (this.autotask.task_type === "checkfailure") {
        return this.autotask.assigned_check !== null ? true : false;
      } else if (this.autotask.task_type === "manual") {
        return true;
      } else {
        return false;
      }
    }
  },
  created() {
    this.getScripts();
  }
};
</script>