<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row items-center">
      <div class="text-h6">Add Windows Service Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="addCheck">
      <q-card-section>
        <q-radio
          v-if="policypk"
          v-model="serviceType"
          val="svcdefault"
          label="Choose from defaults"
          @input="manualServiceName = null; manualSvcDisplayName = null; displayName = null"
        />
        <q-radio
          v-if="policypk"
          v-model="serviceType"
          val="svcmanual"
          label="Enter manually"
          @input="manualServiceName = null; manualSvcDisplayName = null; displayName = null"
        />
        <q-select
          v-if="policypk && serviceType === 'svcdefault'"
          dense
          outlined
          v-model="displayName"
          :options="svcDisplayNames"
          label="Service"
          @input="getRawName"
        />
        <q-input
          v-if="policypk && serviceType === 'svcmanual'"
          outlined
          dense
          v-model="manualServiceName"
          label="Service Name"
        />
        <q-input
          v-if="policypk && serviceType === 'svcmanual'"
          outlined
          dense
          v-model="manualSvcDisplayName"
          label="Display Name"
        />
        <q-select
          v-if="agentpk"
          :rules="[val => !!val || '*Required']"
          dense
          outlined
          v-model="displayName"
          :options="svcDisplayNames"
          label="Service"
          @input="getRawName"
        />
      </q-card-section>
      <q-card-section>
        <q-checkbox
          v-model="passIfStartPending"
          label="PASS if service is in 'Start Pending' mode"
        />
        <q-checkbox v-model="restartIfStopped" label="RESTART service if it's stopped" />
      </q-card-section>
      <q-card-section>
        <q-select
          outlined
          dense
          v-model="failure"
          :options="failures"
          label="Number of consecutive failures before alert"
        />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn label="Add" color="primary" type="submit" />
        <q-btn label="Cancel" v-close-popup />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import { mapState } from "vuex";
import mixins from "@/mixins/mixins";
export default {
  name: "AddWinSvcCheck",
  props: ["agentpk", "policypk"],
  mixins: [mixins],
  data() {
    return {
      serviceType: "svcdefault",
      manualServiceName: "",
      manualSvcDisplayName: "",
      servicesData: [],
      displayName: "",
      rawName: [],
      passIfStartPending: false,
      restartIfStopped: false,
      failure: 2,
      failures: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    };
  },
  computed: {
    svcDisplayNames() {
      return this.servicesData.map(k => k.display_name).sort();
    }
  },
  methods: {
    getServices() {
      if (this.policypk) {
        axios.get("/services/getdefaultservices/").then(r => {
          this.servicesData = Object.freeze(r.data);
        });
      } else {
        axios.get(`/services/${this.agentpk}/services/`).then(r => {
          this.servicesData = Object.freeze([r.data][0].services);
        });
      }
    },
    getRawName() {
      let svc = this.servicesData.find(k => k.display_name === this.displayName);
      this.rawName = [svc].map(j => j.name);
    },
    addCheck() {
      const pk = this.policypk ? { policy: this.policypk } : { pk: this.agentpk };

      let rawname, displayname;

      if (this.policypk) {
        // policy
        if (this.serviceType === "svcdefault") {
          rawname = { rawname: this.rawName[0] };
          displayname = { displayname: this.displayName };
          if (this.rawName.length === 0) {
            this.notifyError("Please select a service");
            return;
          }
        } else if (this.serviceType === "svcmanual") {
          rawname = { rawname: this.manualServiceName };
          displayname = { displayname: this.manualSvcDisplayName };
          if (!this.manualServiceName || !this.manualSvcDisplayName) {
            this.notifyError("All fields required");
            return;
          }
        }
      } else {
        // agent
        rawname = { rawname: this.rawName[0] };
        displayname = { displayname: this.displayName };
      }

      const data = {
        ...pk,
        check_type: "winsvc",
        ...rawname,
        ...displayname,
        passifstartpending: this.passIfStartPending,
        restartifstopped: this.restartIfStopped,
        failures: this.failure
      };

      axios
        .post("/checks/addstandardcheck/", data)
        .then(r => {
          this.$emit("close");
          if (this.policypk) {
            this.$store.dispatch("automation/loadPolicyChecks", this.policypk);
          } else {
            this.$store.dispatch("loadChecks", this.agentpk);
          }
          this.notifySuccess(`${data.displayname} service check added!`);
        })
        .catch(e => this.notifyError(e.response.data.error));
    }
  },
  mounted() {
    this.getServices();
  }
};
</script>