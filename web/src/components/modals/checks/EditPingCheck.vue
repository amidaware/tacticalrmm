<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row items-center">
      <div class="text-h6">Edit Ping Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="editCheck">
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
  name: "EditPingCheck",
  props: ["agentpk", "editCheckPK"],
  mixins: [mixins],
  data() {
    return {
      failure: null,
      failures: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
      pingname: "",
      pingip: ""
    };
  },
  methods: {
    getCheck() {
      axios
        .get(`/checks/getstandardcheck/ping/${this.editCheckPK}/`)
        .then(r => {
          this.failure = r.data.failures;
          this.pingname = r.data.name;
          this.pingip = r.data.ip;
        });
    },
    editCheck() {
      const data = {
        pk: this.editCheckPK,
        check_type: "ping",
        failures: this.failure,
        name: this.pingname,
        ip: this.pingip
      };
      axios
        .patch("/checks/editstandardcheck/", data)
        .then(r => {
          this.$emit("close");
          this.$store.dispatch("loadChecks", this.agentpk);
          this.notifySuccess("Ping check was edited!");
        })
        .catch(e => this.notifyError(e.response.data.error));
    }
  },
  mounted() {
    this.getCheck();
  }
};
</script>