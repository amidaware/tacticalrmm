<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row items-center">
      <div class="text-h6">Edit Disk Space Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="editCheck">
      <q-card-section>
        <q-select outlined disable v-model="diskToEdit" :options="disks" label="Disk" />
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
        <q-btn label="Edit" color="primary" type="submit" />
        <q-btn label="Cancel" v-close-popup />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
export default {
  name: "EditDiskSpaceCheck",
  props: ["editCheckPK", "agentpk"],
  mixins: [mixins],
  data() {
    return {
      threshold: null,
      disks: [],
      diskToEdit: "",
      failure: null,
      failures: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    };
  },
  methods: {
    getCheck() {
      axios
        .get(`/checks/getstandardcheck/diskspace/${this.editCheckPK}/`)
        .then(r => {
          this.disks = [r.data.disk];
          this.diskToEdit = r.data.disk;
          this.threshold = r.data.threshold;
          this.failure = r.data.failures;
        });
    },
    editCheck() {
      const data = {
        check_type: "diskspace",
        pk: this.editCheckPK,
        threshold: this.threshold,
        failures: this.failure
      };
      axios
        .patch("/checks/editstandardcheck/", data)
        .then(r => {
          this.$emit("close");
          this.$store.dispatch("loadChecks", this.agentpk);
          this.notifySuccess("Disk space check was edited!");
        })
        .catch(e => this.notifyError(e.response.data.error));
    }
  },
  mounted() {
    this.getCheck();
  }
};
</script>