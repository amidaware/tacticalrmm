<template>
  <q-card>
    <q-bar>
      Update Agents
      <q-space />
      <q-btn dense flat icon="close" v-close-popup>
        <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
      </q-btn>
    </q-bar>
    <q-separator />
    <q-card-section>
      Select Version
      <q-select
        square
        dense
        options-dense
        outlined
        v-model="version"
        :options="Object.values(versions)"
      />
    </q-card-section>
    <q-card-section v-show="version !== null">
      Select Agent
      <br />
      <hr />
      <q-checkbox v-model="selectAll" label="Select All" @input="selectAllAction" />
      <hr />
      <q-option-group v-model="group" :options="agentOptions" color="green" type="checkbox" />
    </q-card-section>
    <q-card-section>
      <q-btn v-show="group.length !== 0" label="Update" color="primary" @click="update" />
    </q-card-section>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
export default {
  name: "UpdateAgents",
  mixins: [mixins],
  data() {
    return {
      versions: {},
      version: null,
      agents: [],
      group: [],
      selectAll: false,
    };
  },
  methods: {
    selectAllAction() {
      this.selectAll ? (this.group = this.agentPKs) : (this.group = []);
    },
    getVersions() {
      this.$q.loading.show();
      axios
        .get("/agents/getagentversions/")
        .then(r => {
          this.versions = r.data.versions;
          this.agents = r.data.agents;
          this.$q.loading.hide();
        })
        .catch(() => {
          this.$q.loading.hide();
          this.notifyError("Something went wrong");
        });
    },
    update() {
      const data = { version: this.version, pks: this.group };
      axios
        .post("/agents/updateagents/", data)
        .then(r => {
          this.$emit("close");
          this.notifySuccess("Agents will now be updated");
        })
        .catch(() => this.notifyError("Something went wrong"));
    },
  },
  computed: {
    agentPKs() {
      return this.agents.map(k => k.pk);
    },
    agentOptions() {
      const options = [];
      for (let i of Object.values(this.agents)) {
        let opt = {};
        opt["label"] = `${i.hostname} (${i.client} > ${i.site})`;
        opt["value"] = i.pk;
        options.push(opt);
      }
      return options;
    },
  },
  created() {
    this.getVersions();
  },
};
</script>
