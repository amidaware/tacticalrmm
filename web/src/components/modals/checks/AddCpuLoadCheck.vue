<template>
    <q-card style="min-width: 400px">
        <q-card-section class="row items-center">
        <div class="text-h6">Add CPU Load Check</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-form @submit.prevent="addCheck">
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
            <q-card-actions align="right">
                <q-btn label="Add" color="primary" type="submit" />
                <q-btn label="Cancel" v-close-popup />
            </q-card-actions>
        </q-form>
    </q-card>
</template>

<script>
import axios from "axios";
import { mapState } from 'vuex';
import mixins from "@/mixins/mixins";
export default {
  name: "AddCpuLoadCheck",
  props: ["agentpk"],
  mixins: [mixins],
  data() {
    return {
      threshold: 85
    };
  },
  methods: {
    addCheck() {
      const data = {
        pk: this.agentpk,
        check_type: "cpuload",
        threshold: this.threshold
      };
      axios
        .post("/checks/addstandardcheck/", data)
        .then(r => {
          this.$emit("close");
          this.$store.dispatch("loadChecks", this.agentpk);
          this.notifySuccess("CPU load check was added!");
        })
        .catch(e => this.notifyError(e.response.data.error));
    }
  }
};
</script>