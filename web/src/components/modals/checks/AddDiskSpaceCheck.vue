<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row items-center">
      <div class="text-h6">Add Disk Space Check</div>
      <q-space />
      <q-btn
        icon="close"
        flat
        round
        dense
        v-close-popup
      />
    </q-card-section>

    <q-form @submit.prevent="addCheck">
      <q-card-section>
        <q-select
          outlined
          v-model="firstdisk"
          :options="disks"
          label="Disk"
        />
      </q-card-section>
      <q-card-section>
        <q-input
          outlined
          v-model.number="threshold"
          label="Threshold (%)"
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
        <q-btn
          label="Add"
          color="primary"
          type="submit"
        />
        <q-btn
          label="Cancel"
          v-close-popup
        />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import { mapState } from "vuex";
import mixins from "@/mixins/mixins";
export default {
  name: "AddDiskSpaceCheck",
  props: ["agentpk", "policypk"],
  mixins: [mixins],
  data() {
    return {
      threshold: 25,
      disks: [],
      firstdisk: "",
      failure: 2,
      failures: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    };
  },
  methods: {
    getDisks() {
      if (this.policypk) {
        axios.get("/checks/getalldisks/").then(r => {
          this.disks = r.data;
          this.firstdisk = "C:";
        });
      } else {
        axios.get(`/checks/getdisks/${this.agentpk}/`).then(r => {
          this.disks = Object.keys(r.data);
          this.firstdisk = Object.keys(r.data)[0];
        });
      }

    },
    addCheck() {
      const pk = (this.policypk) ? { policy: this.policypk } : { pk: this.agentpk }
      const data = {
        ...pk,
        check_type: "diskspace",
        disk: this.firstdisk,
        threshold: this.threshold,
        failure: this.failure
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

          this.notifySuccess(`Disk check for drive ${data.disk} was added!`);
        })
        .catch(e => this.notifyError(e.response.data.error));
    }
  },
  mounted() {
    this.getDisks();
  }
};
</script>