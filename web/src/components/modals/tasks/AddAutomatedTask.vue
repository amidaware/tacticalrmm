<template>
  <q-card v-if="scripts.length === 0" class="q-pa-xs" style="min-width: 400px">
    <q-card-section class="row items-center">
      <div class="text-h6">Add Automated Task</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>
    <q-card-section>
      <p>You need to upload a script/task first</p>
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
            v-model="scriptPk"
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
            v-model="taskName"
            label="Descriptive name of task"
          />
        </q-card-section>
        <q-card-section>
          <q-input
            :rules="[val => !!val || '*Required']"
            outlined
            dense
            v-model.number="timeout"
            type="number"
            label="Maximum permitted execution time (seconds)"
          />
        </q-card-section>
      </q-step>

      <q-step :name="2" title="Choose Schedule" :done="step2Done" :error="!step2Done">
        <q-radio v-model="trigger" val="daily" label="Scheduled" />
        <q-radio v-model="trigger" val="checkfailure" label="On check failure" />
        <q-radio v-model="trigger" val="manual" label="Manual" />
        <div v-if="trigger === 'daily'" class="row q-pa-lg">
          <div class="col-3">
            Run on Days:
            <q-option-group :options="dayOptions" label="Days" type="checkbox" v-model="days" />
          </div>
          <div class="col-2"></div>
          <div class="col-6">
            At time:
            <q-time v-model="time" />
          </div>
          <div class="col-1"></div>
        </div>
        <div v-else-if="trigger === 'checkfailure'" class="q-pa-lg">
          When Check Fails:
          <q-select
            :rules="[val => !!val || '*Required']"
            dense
            outlined
            v-model="assignedCheck"
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
import { mapState } from "vuex";
import { mapGetters } from "vuex";
import mixins from "@/mixins/mixins";

export default {
  name: "AddAutomatedTask",
  mixins: [mixins],
  data() {
    return {
      step: 1,
      trigger: "daily",
      time: null,
      taskName: null,
      scriptPk: null,
      assignedCheck: null,
      timeout: 120,
      days: [],
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
    addTask() {
      if (!this.step1Done || !this.step2Done) {
        this.notifyError("Some steps incomplete");
      } else {
        const data = {
          agent: this.selectedAgentPk,
          name: this.taskName,
          script: this.scriptPk,
          trigger: this.trigger,
          check: this.assignedCheck,
          time: this.time,
          days: this.days,
          timeout: this.timeout
        };
        axios
          .post(`/tasks/${this.selectedAgentPk}/automatedtasks/`, data)
          .then(r => {
            this.$emit("close");
            this.$store.dispatch("loadAutomatedTasks", this.selectedAgentPk);
            this.$store.dispatch("loadChecks", this.selectedAgentPk);
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
    ...mapState({
      checks: state => state.agentChecks
    }),
    allChecks() {
      return [
        ...this.checks.diskchecks,
        ...this.checks.cpuloadchecks,
        ...this.checks.memchecks,
        ...this.checks.scriptchecks,
        ...this.checks.winservicechecks,
        ...this.checks.pingchecks,
        ...this.checks.eventlogchecks
      ];
    },
    checksOptions() {
      const r = [];
      this.allChecks.forEach(k => {
        // some checks may have the same primary key so add the check type to make them unique
        r.push({ label: k.readable_desc, value: `${k.id}|${k.check_type}` });
      });
      return r;
    },
    scriptOptions() {
      const r = [];
      this.scripts.forEach(k => {
        r.push({ label: k.name, value: k.id });
      });
      return r;
    },
    step1Done() {
      return this.step > 1 && this.scriptPk !== null && this.taskName !== null ? true : false;
    },
    step2Done() {
      if (this.trigger === "daily") {
        return this.days !== null && this.days.length !== 0 && this.time !== null ? true : false;
      } else if (this.trigger === "checkfailure") {
        return this.assignedCheck !== null && this.assignedCheck.length !== 0 ? true : false;
      } else if (this.trigger === "manual") {
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