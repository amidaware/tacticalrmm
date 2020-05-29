<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row items-center">
      <div v-if="mode === 'add'" class="text-h6">Add Disk Space Check</div>
      <div v-else-if="mode === 'edit'" class="text-h6">Edit Disk Space Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="addCheck">
      <q-card-section>
        <q-select outlined v-model="diskcheck.disk" :options="diskOptions" label="Disk" />
      </q-card-section>
      <q-card-section>
        <q-input
          outlined
          v-model.number="diskcheck.threshold"
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
          v-model="diskcheck.fails_b4_alert"
          :options="failOptions"
          label="Number of consecutive failures before alert"
        />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn v-if="mode === 'add'" label="Add" color="primary" type="submit" />
        <q-btn v-else-if="mode === 'edit'" label="Edit" color="primary" type="submit" />
        <q-btn label="Cancel" v-close-popup />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import { mapState, mapGetters } from "vuex";
import mixins from "@/mixins/mixins";
export default {
  name: "DiskSpaceCheck",
  props: {
    agentpk: Number,
    policypk: Number,
    mode: String
  },
  mixins: [mixins],
  data() {
    return {
      diskcheck: {},
      diskOptions: [],
      failOptions: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    };
  },
  methods: {
    setDiskOptions() {
      if (this.policypk) {
        axios.get("/checks/getalldisks/").then(r => {
          this.diskOptions = r.data;
          this.diskcheck.disk = "C:";
        });
      } else {
        this.diskOptions = Object.keys(this.agentDisks);
        this.diskcheck.disk = this.diskOptions[0];
      }
    },
    addCheck() {
      const pk = this.policypk ? { policy: this.policypk } : { pk: this.agentpk };
      const data = {
        ...pk,
        check: this.diskcheck
      };
      axios
        .post("/checks/checks/", data)
        .then(r => {
          this.$emit("close");

          if (this.policypk) {
            this.$store.dispatch("automation/loadPolicyChecks", this.policypk);
          } else {
            this.$store.dispatch("loadChecks", this.agentpk);
          }

          this.notifySuccess(r.data);
        })
        .catch(e => this.notifyError(e.response.data));
    }
  },
  computed: {
    ...mapGetters(["agentDisks"])
  },
  created() {
    if (this.mode === "add") {
      this.diskcheck.check_type = "diskspace";
      this.diskcheck.threshold = 25;
      this.diskcheck.fails_b4_alert = 1;
      this.setDiskOptions();
    }
  }
};
</script>