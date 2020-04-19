<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row items-center">
      <div class="text-h6">Edit CPU Load Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="editCheck">
      <q-card-section>
        <q-input
          outlined
          v-model.number="threshold"
          label="Alert if average utilization > (%)"
          :rules="[ 
                    val => !!val || '*Required',
                    val => val >= 1 || 'Minimum threshold is 1',
                    val => val < 100 || 'Maximum threshold is 99'
                ]"
        />
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
  name: "EditCpuLoadCheck",
  props: ["agentpk", "policypk", "editCheckPK"],
  mixins: [mixins],
  data() {
    return {
      threshold: null,
      failure: null,
      failures: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    };
  },
  methods: {
    getCheck() {
      axios
        .get(`/checks/getstandardcheck/cpuload/${this.editCheckPK}/`)
        .then(r => {
          this.threshold = r.data.cpuload;
          this.failure = r.data.failures;
        });
    },
    editCheck() {
      const data = {
        pk: this.editCheckPK,
        check_type: "cpuload",
        threshold: this.threshold,
        failure: this.failure
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
          
          this.notifySuccess("CPU load check was edited!");
        })
        .catch(e => this.notifyError(e.response.data.error));
    }
  },
  mounted() {
    this.getCheck();
  }
};
</script>