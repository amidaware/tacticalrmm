<template>
  <q-card v-if="scripts.length === 0" style="min-width: 400px">
    <q-card-section class="row items-center">
      <div class="text-h6">Add Script Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>
    <q-card-section>
      <p>You need to upload a script first</p>
      <p>Settings -> Script Manager</p>
    </q-card-section>
  </q-card>
  <q-card v-else style="min-width: 400px">
    <q-card-section class="row items-center">
      <div v-if="mode === 'add'" class="text-h6">Add Script Check</div>
      <div v-else-if="mode === 'edit'" class="text-h6">Edit Script Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="mode === 'add' ? addCheck() : editCheck()">
      <q-card-section>
        <q-select
          :rules="[val => !!val || '*Required']"
          dense
          options-dense
          outlined
          v-model="scriptcheck.script"
          :options="scriptOptions"
          label="Select script"
          map-options
          emit-value
          :disable="this.mode === 'edit'"
        />
      </q-card-section>
      <q-card-section>
        <q-input
          outlined
          dense
          v-model.number="scriptcheck.timeout"
          label="Timeout (seconds)"
          :rules="[ 
              val => !!val || '*Required',
              val => val >= 10 || 'Minimum is 10 seconds',
              val => val <= 86400 || 'Maximum is 86400 seconds'
          ]"
        />
      </q-card-section>
      <q-card-section>
        <q-select
          outlined
          dense
          options-dense
          v-model="scriptcheck.fails_b4_alert"
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
import mixins from "@/mixins/mixins";
import { mapGetters, mapState } from "vuex";
export default {
  name: "ScriptCheck",
  props: {
    agentpk: Number,
    policypk: Number,
    mode: String,
    checkpk: Number,
  },
  mixins: [mixins],
  data() {
    return {
      scriptcheck: {
        check_type: "script",
        script: null,
        timeout: 120,
        fails_b4_alert: 1,
      },
      failOptions: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    };
  },
  computed: {
    ...mapGetters(["scripts"]),
    scriptOptions() {
      const ret = [];
      this.scripts.forEach(i => {
        ret.push({ label: i.name, value: i.id });
      });
      return ret;
    },
  },
  methods: {
    getCheck() {
      axios.get(`/checks/${this.checkpk}/check/`).then(r => {
        this.scriptcheck = r.data;
        this.scriptcheck.script = r.data.script.id;
      });
    },
    addCheck() {
      const pk = this.policypk ? { policy: this.policypk } : { pk: this.agentpk };
      const data = {
        ...pk,
        check: this.scriptcheck,
      };
      axios
        .post("/checks/checks/", data)
        .then(r => {
          this.$emit("close");
          this.reloadChecks();
          this.notifySuccess(r.data);
        })
        .catch(e => this.notifyError(e.response.data.non_field_errors));
    },
    editCheck() {
      axios
        .patch(`/checks/${this.checkpk}/check/`, this.scriptcheck)
        .then(r => {
          this.$emit("close");
          this.reloadChecks();
          this.notifySuccess(r.data);
        })
        .catch(e => this.notifyError(e.response.data.non_field_errors));
    },
    reloadChecks() {
      if (this.policypk) {
        this.$store.dispatch("automation/loadPolicyChecks", this.policypk);
      } else {
        this.$store.dispatch("loadChecks", this.agentpk);
      }
    },
  },
  created() {
    if (this.mode === "edit") {
      this.getCheck();
    }
  },
};
</script>