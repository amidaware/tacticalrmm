<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row items-center">
      <div class="text-h6">Add Windows Service Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="addCheck">
      
      <q-card-section>
        <q-select :rules="[val => !!val || '*Required']" dense outlined v-model="displayName" :options="svcDisplayNames" label="Service" @input="getRawName" />
        
      </q-card-section>
      <q-card-section>
        <q-checkbox v-model="passIfStartPending" label="PASS if service is in 'Start Pending' mode" />
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
  props: ["agentpk"],
  mixins: [mixins],
  data() {
    return {
      servicesData: [],
      displayName: "",
      rawName: [],
      passIfStartPending: false,
      restartIfStopped: false,
      failure: 1,
      failures: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    };
  },
  computed: {
    svcDisplayNames() {
      return this.servicesData.map(k => k.display_name).sort()
    }
  },
  methods: {
    async getServices() {
      try {
        let r = await axios.get(`/services/${this.agentpk}/services/`);
        this.servicesData = Object.freeze([r.data][0].services);
      } catch (e) {
        console.log(`ERROR!: ${e}`);
      }
    },
    getRawName() {
      let svc = this.servicesData.find(k => k.display_name === this.displayName);
      this.rawName = [svc].map(j => j.name);
    },
    addCheck() {
      const data = {
        pk: this.agentpk,
        check_type: "winsvc",
        displayname: this.displayName,
        rawname: this.rawName[0],
        passifstartpending: this.passIfStartPending,
        restartifstopped: this.restartIfStopped,
        failures: this.failure
      };
      axios
        .post("/checks/addstandardcheck/", data)
        .then(r => {
          this.$emit("close");
          this.$store.dispatch("loadChecks", this.agentpk);
          this.notifySuccess(`${data.displayname} service check added!`);
        })
        .catch(e => this.notifyError(e.response.data.error));
    }
  },
  mounted() {
    this.getServices();
  },
};
</script>