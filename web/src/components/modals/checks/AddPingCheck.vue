<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row items-center">
      <div class="text-h6">Add Ping Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="addCheck">
      <q-card-section>
        <q-input
          outlined
          v-model="pingname"
          label="Descriptive Name"
          :rules="[val => !!val || '*Required']"
        />
      </q-card-section>
      <q-card-section>
        <q-input
          outlined
          v-model="pingip"
          label="Hostname or IP"
          :rules="[val => !!val || '*Required']"
        />
      </q-card-section>
      <q-card-section>
        <q-select
          outlined
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
  name: "AddPingCheck",
  props: ["agentpk", "policypk"],
  mixins: [mixins],
  data() {
    return {
      failure: 5,
      failures: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
      pingname: "",
      pingip: ""
    };
  },
  methods: {
    addCheck() {
      let pk = (this.policypk) ? {policy: this.policypk} : {pk: this.agentpk}

      const data = {
        ...pk,
        check_type: "ping",
        failures: this.failure,
        name: this.pingname,
        ip: this.pingip,
      };

      axios.post("/checks/addstandardcheck/", data)
        .then(r => {
          this.$emit("close");

          if (this.policypk) {
            this.$store.dispatch("loadPolicyChecks", this.policypk);
          } else {
            this.$store.dispatch("loadChecks", this.agentpk);
          }

          this.notifySuccess("Ping check was added!");
        })
        .catch(e => {
          this.notifyError(e.response.data);
          console.log(e.response.data)
        });
    }
  }
};
</script>