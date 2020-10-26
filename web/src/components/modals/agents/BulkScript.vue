<template>
  <q-card style="min-width: 50vw">
    <q-card-section class="row items-center">
      <div class="text-h6">
        Run Bulk Script
        <div class="text-caption">Run a script on multiple agents in parallel</div>
      </div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
      <br />
    </q-card-section>
    <q-form @submit.prevent="send">
      <q-card-section>
        <div class="q-pa-none">
          <p>Choose Target</p>
          <div class="q-gutter-sm">
            <q-radio dense v-model="target" val="client" label="Client" @input="agentMultiple = []" />
            <q-radio dense v-model="target" val="site" label="Site" @input="agentMultiple = []" />
            <q-radio dense v-model="target" val="agents" label="Selected Agents" />
            <q-radio dense v-model="target" val="all" label="All Agents" @input="agentMultiple = []" />
          </div>
        </div>
      </q-card-section>

      <q-card-section v-if="tree !== null && client !== null && target === 'client'">
        <q-select
          dense
          :rules="[val => !!val || '*Required']"
          outlined
          options-dense
          label="Select client"
          v-model="client"
          :options="Object.keys(tree).sort()"
        />
      </q-card-section>

      <q-card-section v-if="tree !== null && client !== null && target === 'site'">
        <q-select
          dense
          :rules="[val => !!val || '*Required']"
          outlined
          options-dense
          label="Select client"
          v-model="client"
          :options="Object.keys(tree).sort()"
          @input="site = sites[0]"
        />
        <q-select
          dense
          :rules="[val => !!val || '*Required']"
          outlined
          options-dense
          label="Select site"
          v-model="site"
          :options="sites"
        />
      </q-card-section>

      <q-card-section v-if="agents.length !== 0 && target === 'agents'">
        <q-select
          dense
          options-dense
          filled
          v-model="agentMultiple"
          multiple
          :options="agents"
          use-chips
          stack-label
          map-options
          emit-value
          label="Select Agents"
        />
      </q-card-section>

      <q-card-section>
        <q-select
          :rules="[val => !!val || '*Required']"
          dense
          outlined
          v-model="scriptPK"
          :options="scriptOptions"
          label="Select script"
          map-options
          emit-value
          options-dense
        />
      </q-card-section>
      <q-card-section>
        <q-select
          label="Script Arguments (press Enter after typing each argument)"
          filled
          dense
          v-model="args"
          use-input
          use-chips
          multiple
          hide-dropdown-icon
          input-debounce="0"
          new-value-mode="add"
        />
      </q-card-section>
      <q-card-section>
        <q-input
          v-model.number="timeout"
          dense
          outlined
          type="number"
          style="max-width: 150px"
          label="Timeout (seconds)"
          stack-label
          :rules="[
            val => !!val || '*Required',
            val => val >= 10 || 'Minimum is 10 seconds',
            val => val <= 25200 || 'Maximum is 25,200 seconds',
          ]"
        />
      </q-card-section>
      <q-card-actions align="center">
        <q-btn label="Run" color="primary" class="full-width" type="submit" />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";
import { mapGetters } from "vuex";

export default {
  name: "BulkScript",
  mixins: [mixins],
  data() {
    return {
      target: "client",
      scriptPK: null,
      timeout: 900,
      tree: null,
      client: null,
      site: null,
      agents: [],
      agentMultiple: [],
      args: [],
    };
  },
  computed: {
    ...mapGetters(["scripts"]),
    sites() {
      if (this.tree !== null && this.client !== null) {
        this.site = this.tree[this.client].sort()[0];
        return this.tree[this.client].sort();
      }
    },
    scriptOptions() {
      const ret = [];
      this.scripts.forEach(i => {
        ret.push({ label: i.name, value: i.id });
      });
      return ret.sort((a, b) => a.label.localeCompare(b.label));
    },
  },
  methods: {
    send() {
      this.$q.loading.show();
      const data = {
        mode: "script",
        target: this.target,
        client: this.client,
        site: this.site,
        agentPKs: this.agentMultiple,
        scriptPK: this.scriptPK,
        timeout: this.timeout,
        args: this.args,
      };
      this.$axios
        .post("/agents/bulk/", data)
        .then(r => {
          this.$q.loading.hide();
          this.$emit("close");
          this.notifySuccess(r.data);
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data);
        });
    },
    getTree() {
      this.$axios.get("/clients/loadclients/").then(r => {
        this.tree = r.data;
        this.client = Object.keys(r.data).sort()[0];
      });
    },
    getAgents() {
      this.$axios.get("/agents/listagentsnodetail/").then(r => {
        const ret = [];
        r.data.forEach(i => {
          ret.push({ label: i.hostname, value: i.pk });
        });
        this.agents = Object.freeze(ret.sort((a, b) => a.label.localeCompare(b.label)));
      });
    },
  },
  created() {
    this.getTree();
    this.getAgents();
  },
};
</script>