<template>
  <q-card style="min-width: 50vw">
    <q-card-section class="row items-center">
      <div class="text-h6">Bulk Patch Management</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
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
        <div class="q-pa-none">
          <p>Action</p>
          <div class="q-gutter-sm">
            <q-radio dense v-model="mode" val="scan" label="Run Patch Status Scan" />
            <q-radio dense v-model="mode" val="install" label="Install Pending Patches Now" />
          </div>
        </div>
      </q-card-section>

      <q-card-actions align="center">
        <q-btn label="Send" color="primary" class="full-width" type="submit" />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "BulkPatchManagement",
  mixins: [mixins],
  data() {
    return {
      target: "client",
      tree: null,
      client: null,
      site: null,
      agents: [],
      agentMultiple: [],
      mode: "scan",
    };
  },
  computed: {
    sites() {
      if (this.tree !== null && this.client !== null) {
        this.site = this.tree[this.client].sort()[0];
        return this.tree[this.client].sort();
      }
    },
  },
  methods: {
    send() {
      this.$q.loading.show();
      const data = {
        mode: this.mode,
        target: this.target,
        client: this.client,
        site: this.site,
        agentPKs: this.agentMultiple,
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