<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row items-center">
      <div class="text-h6">Edit Windows Service Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="editCheck">
      
      <q-card-section>
        <q-select disable dense outlined v-model="displayName" :options="svcDisplayNames" label="Service" />
        
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
        <q-btn label="Edit" color="primary" type="submit" />
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
  name: "EditWinSvcCheck",
  props: ["agentpk", "editCheckPK"],
  mixins: [mixins],
  data() {
    return {
      displayName: "",
      svcDisplayNames: [],
      passIfStartPending: null,
      restartIfStopped: null,
      failure: null,
      failures: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    };
  },
  methods: {
    async getService() {
      try {
        let r = await axios.get(`/checks/getstandardcheck/winsvc/${this.editCheckPK}/`);
        this.svcDisplayNames = [r.data.svc_display_name];
        this.displayName = r.data.svc_display_name;
        this.passIfStartPending = r.data.pass_if_start_pending;
        this.restartIfStopped = r.data.restart_if_stopped;
        this.failure = r.data.failures;
      } catch (e) {
        console.log(`ERROR!: ${e}`);
      }
    },
    editCheck() {
      const data = {
        pk: this.editCheckPK,
        check_type: "winsvc",
        failures: this.failure,
        passifstartpending: this.passIfStartPending,
        restartifstopped: this.restartIfStopped
      };
      axios
        .patch("/checks/editstandardcheck/", data)
        .then(r => {
          this.$emit("close");

          if (this.policypk) {
            this.$store.dispatch("loadPolicyChecks", this.policypk);
          } else {
            this.$store.dispatch("loadChecks", this.agentpk);
          }
          
          this.notifySuccess("Windows service check was edited!");
        })
        .catch(e => this.notifyError(e.response.data.error));
    }
  },
  mounted() {
    this.getService();
  },
};
</script>