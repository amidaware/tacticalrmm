<template>
  <q-card style="min-width: 40vw">
    <q-card-section class="row items-center">
      <div v-if="mode === 'add'" class="text-h6">Add Service Check</div>
      <div v-else-if="mode === 'edit'" class="text-h6">Edit Service Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="mode === 'add' ? addCheck() : editCheck()">
      <q-card-section>
        <!-- policy check, either choose from a list of default services or enter manually -->
        <q-radio
          v-if="policypk && this.mode !== 'edit'"
          v-model="winsvccheck.svc_policy_mode"
          val="default"
          label="Choose from defaults"
          @input="clearServiceOptions"
        />
        <q-radio
          v-if="policypk && this.mode !== 'edit'"
          v-model="winsvccheck.svc_policy_mode"
          val="manual"
          label="Enter manually"
          @input="clearServiceOptions"
        />
        <q-select
          v-if="policypk && winsvccheck.svc_policy_mode === 'default' && this.mode !== 'edit'"
          :rules="[val => !!val || '*Required']"
          dense
          options-dense
          outlined
          v-model="winsvccheck.svc_name"
          :options="serviceOptions"
          label="Service"
          map-options
          emit-value
          @input="getDisplayName"
        />
        <!-- disable selection if editing -->
        <q-select
          v-if="policypk && winsvccheck.svc_policy_mode === 'default' && this.mode === 'edit'"
          disable
          dense
          options-dense
          outlined
          v-model="winsvccheck.svc_name"
          :options="serviceOptions"
          label="Service"
          map-options
          emit-value
        />
        <q-input
          v-if="policypk && winsvccheck.svc_policy_mode === 'manual'"
          :rules="[val => !!val || '*Required']"
          outlined
          dense
          v-model="winsvccheck.svc_name"
          label="Service Name"
        />
        <q-input
          v-if="policypk && winsvccheck.svc_policy_mode === 'manual'"
          :rules="[val => !!val || '*Required']"
          outlined
          dense
          v-model="winsvccheck.svc_display_name"
          label="Display Name"
        />
        <!-- agent check -->
        <!-- disable selection if editing -->
        <q-select
          v-if="agentpk"
          :rules="[val => !!val || '*Required']"
          dense
          options-dense
          outlined
          v-model="winsvccheck.svc_name"
          :options="serviceOptions"
          label="Service"
          map-options
          emit-value
          @input="getDisplayName"
          :disable="this.mode === 'edit'"
        />
      </q-card-section>
      <q-card-section>
        <q-checkbox v-model="winsvccheck.pass_if_start_pending" label="PASS if service is in 'Start Pending' mode" />
        <br />
        <q-checkbox v-model="winsvccheck.pass_if_svc_not_exist" label="PASS if service doesn't exist" />
        <br />
        <q-checkbox v-model="winsvccheck.restart_if_stopped" label="Restart service if it's stopped" />
      </q-card-section>
      <q-card-section>
        <q-select
          outlined
          dense
          options-dense
          map-options
          emit-value
          v-model="winsvccheck.alert_severity"
          :options="severityOptions"
          label="Alert Severity"
        />
      </q-card-section>
      <q-card-section>
        <q-select
          outlined
          dense
          options-dense
          v-model="winsvccheck.fails_b4_alert"
          :options="failOptions"
          label="Number of consecutive failures before alert"
        />
      </q-card-section>
      <q-card-section>
        <q-input
          dense
          outlined
          type="number"
          v-model.number="winsvccheck.run_interval"
          label="Run this check every (seconds)"
          hint="Setting this value to anything other than 0 will override the 'Run checks every' setting on the agent"
        />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn v-if="mode === 'add'" label="Add" color="primary" type="submit" />
        <q-btn v-else-if="mode === 'edit'" label="Edit" color="primary" type="submit" />
        <q-btn label="Cancel" v-close-popup />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";
import { mapGetters } from "vuex";
export default {
  name: "WinSvcCheck",
  props: {
    agentpk: Number,
    policypk: Number,
    mode: String,
    checkpk: Number,
  },
  mixins: [mixins],
  data() {
    return {
      winsvccheck: {
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
      severityOptions: [
        { label: "Informational", value: "info" },
        { label: "Warning", value: "warning" },
        { label: "Error", value: "error" },
      ],
      svcData: [],
      failOptions: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    };
  },
  computed: {
    ...mapGetters(["agentServices"]),

    serviceOptions() {
      const ret = [];
      this.svcData.forEach(i => {
        ret.push({ label: i.display_name, value: i.name });
      });
      // sort alphabetically by display name
      return ret.sort((a, b) => a.label.localeCompare(b.label));
    },
  },
  methods: {
    clearServiceOptions() {
      this.winsvccheck.svc_name = null;
      this.winsvccheck.svc_display_name = null;
    },
    setServices() {
      if (this.policypk) {
        this.$axios
          .get("/services/defaultservices/")
          .then(r => {
            this.svcData = Object.freeze(r.data);
            this.winsvccheck.svc_policy_mode = "default";
          })
          .catch(e => {});
      } else {
        this.svcData = Object.freeze(this.agentServices);
      }
    },
    getDisplayName() {
      this.winsvccheck.svc_display_name = this.serviceOptions.find(i => i.value === this.winsvccheck.svc_name).label;
    },
    getCheck() {
      this.$axios
        .get(`/checks/${this.checkpk}/check/`)
        .then(r => (this.winsvccheck = r.data))
        .catch(e => {});
    },
    addCheck() {
      const pk = this.policypk ? { policy: this.policypk } : { pk: this.agentpk };
      const data = {
        ...pk,
        check: this.winsvccheck,
      };
      this.$axios
        .post("/checks/checks/", data)
        .then(r => {
          this.$emit("close");
          this.reloadChecks();
          this.notifySuccess(r.data);
        })
        .catch(e => {});
    },
    editCheck() {
      this.$axios
        .patch(`/checks/${this.checkpk}/check/`, this.winsvccheck)
        .then(r => {
          this.$emit("close");
          this.reloadChecks();
          this.notifySuccess(r.data);
        })
        .catch(e => {});
    },
    reloadChecks() {
      if (this.agentpk) {
        this.$store.dispatch("loadChecks", this.agentpk);
      }
    },
  },
  created() {
    this.setServices();
  },
  mounted() {
    if (this.mode === "edit") {
      this.getCheck();
    }
  },
};
</script>