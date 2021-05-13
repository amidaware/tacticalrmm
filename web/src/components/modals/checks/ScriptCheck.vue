<template>
  <q-card v-if="scriptOptions.length === 0" style="min-width: 400px">
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
  <q-card v-else style="min-width: 50vw">
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
          @input="setScriptDefaults"
        >
          <template v-slot:option="scope">
            <q-item
              v-if="!scope.opt.category"
              v-bind="scope.itemProps"
              v-on="scope.itemProps.itemEvents"
              class="q-pl-lg"
            >
              <q-item-section>
                <q-item-label v-html="scope.opt.label"></q-item-label>
              </q-item-section>
            </q-item>
            <q-item-label v-if="scope.opt.category" v-bind="scope.itemProps" header class="q-pa-sm">{{
              scope.opt.category
            }}</q-item-label>
          </template>
        </q-select>
      </q-card-section>
      <q-card-section>
        <q-select
          dense
          label="Script Arguments (press Enter after typing each argument)"
          filled
          v-model="scriptcheck.script_args"
          use-input
          use-chips
          multiple
          hide-dropdown-icon
          input-debounce="0"
          new-value-mode="add"
        />
      </q-card-section>
      <q-card-section>
        <q-select
          dense
          label="Informational return codes (press Enter after typing each code)"
          filled
          v-model="scriptcheck.info_return_codes"
          use-input
          use-chips
          multiple
          hide-dropdown-icon
          input-debounce="0"
          new-value-mode="add-unique"
          @new-value="validateRetcode"
        />
      </q-card-section>
      <q-card-section>
        <q-select
          dense
          label="Warning return codes (press Enter after typing each code)"
          filled
          v-model="scriptcheck.warning_return_codes"
          use-input
          use-chips
          multiple
          hide-dropdown-icon
          input-debounce="0"
          new-value-mode="add-unique"
          @new-value="validateRetcode"
        />
      </q-card-section>
      <q-card-section>
        <q-input outlined dense v-model.number="scriptcheck.timeout" label="Timeout (seconds)" />
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
      <q-card-section>
        <q-input
          outlined
          dense
          type="number"
          v-model.number="scriptcheck.run_interval"
          label="Run this check every (seconds)"
          hint="Setting this value to anything other than 0 will override the 'Run checks every' setting on the agent"
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
import mixins from "@/mixins/mixins";
import { mapGetters } from "vuex";

export default {
  name: "ScriptCheck",
  emits: ["close"],
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
        script_args: [],
        timeout: 120,
        fails_b4_alert: 1,
        info_return_codes: [],
        warning_return_codes: [],
        run_interval: 0,
      },
      scriptOptions: [],
      failOptions: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    };
  },
  computed: {
    ...mapGetters(["showCommunityScripts"]),
  },
  methods: {
    getCheck() {
      this.$axios
        .get(`/checks/${this.checkpk}/check/`)
        .then(r => {
          this.scriptcheck = r.data;
          this.scriptcheck.script = r.data.script.id;
        })
        .catch(e => {});
    },
    addCheck() {
      const pk = this.policypk ? { policy: this.policypk } : { pk: this.agentpk };
      const data = {
        ...pk,
        check: this.scriptcheck,
      };
      this.$axios
        .post("/checks/checks/", data)
        .then(r => {
          this.$emit("close");
          this.reloadChecks();
          this.notifySuccess(r.data);
        })
        .catch(e => {});
    },
    editCheck() {
      this.$axios
        .patch(`/checks/${this.checkpk}/check/`, this.scriptcheck)
        .then(r => {
          this.$emit("close");
          this.reloadChecks();
          this.notifySuccess(r.data);
        })
        .catch(e => {});
    },
    setScriptDefaults() {
      const script = this.scriptOptions.find(i => i.value === this.scriptcheck.script);

      this.scriptcheck.timeout = script.timeout;
      this.scriptcheck.script_args = script.args;
    },
    reloadChecks() {
      if (this.agentpk) {
        this.$store.dispatch("loadChecks", this.agentpk);
      }
    },
    validateRetcode(val, done) {
      /^\d+$/.test(val) ? done(val) : done();
    },
  },
  created() {
    if (this.mode === "edit") {
      this.getCheck();
    }

    this.scriptOptions = this.getScriptOptions(this.showCommunityScripts);
  },
};
</script>