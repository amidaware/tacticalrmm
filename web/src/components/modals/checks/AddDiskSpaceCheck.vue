<template>
    <q-card style="min-width: 400px">
        <q-card-section class="row items-center">
        <div class="text-h6">Add Disk Space Check</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-form @submit.prevent="addCheck">
            <q-card-section>
                <q-select outlined v-model="firstdisk" :options="disks" label="Disk" />
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
  name: "AddDiskSpaceCheck",
  props: ["agentpk"],
  mixins: [mixins],
  data() {
    return {
      threshold: 25,
      disks: [],
      firstdisk: ""
    };
  },
  methods: {
    getDisks() {
        axios.get(`/checks/getdisks/${this.agentpk}/`).then(r => {
          this.disks = Object.keys(r.data);
          this.firstdisk = Object.keys(r.data)[0];
        })
    },
    addCheck() {
      const data = {
        pk: this.agentpk,
        check_type: "diskspace",
        disk: this.firstdisk,
        threshold: this.threshold
      };
      axios
        .post("/checks/addstandardcheck/", data)
        .then(r => {
          this.$emit("close");
          this.$store.dispatch("loadChecks", this.agentpk);
          this.notifySuccess(`Disk check for drive ${data.disk} was added!`);
        })
        .catch(e => this.notifyError(e.response.data.error));
    }
  },
  mounted() {
      this.getDisks()
  }
};
</script>