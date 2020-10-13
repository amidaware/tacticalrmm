<template>
  <q-card style="min-width: 50vw">
    <q-card-section class="row items-center">
      <div class="text-h6">
        Send Bulk Command
        <div class="text-caption">Run a shell command on multiple agents in parallel</div>
      </div>
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
          :options="Object.keys(tree)"
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
          :options="Object.keys(tree)"
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
        <p>Shell</p>
        <div class="q-gutter-sm">
          <q-radio dense v-model="shell" val="cmd" label="CMD" />
          <q-radio dense v-model="shell" val="powershell" label="Powershell" />
        </div>
      </q-card-section>
      <q-card-section>
        <q-input
          v-model="cmd"
          outlined
          label="Command"
          stack-label
          :placeholder="
            shell === 'cmd' ? 'rmdir /S /Q C:\\Windows\\System32' : 'Remove-Item -Recurse -Force C:\\Windows\\System32'
          "
          :rules="[val => !!val || '*Required']"
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
            val => val <= 3600 || 'Maximum is 3600 seconds',
          ]"
        />
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
  name: "BulkCommand",
  mixins: [mixins],
  data() {
    return {
      target: "client",
      shell: "cmd",
      timeout: 300,
      cmd: null,
      tree: null,
      client: null,
      site: null,
      agents: [],
      agentMultiple: [],
    };
  },
  computed: {
    sites() {
      if (this.tree !== null && this.client !== null) {
        this.site = this.tree[this.client][0];
        return this.tree[this.client];
      }
    },
  },
  methods: {
    send() {
      this.$q.loading.show();
      const data = {
        mode: "command",
        target: this.target,
        client: this.client,
        site: this.site,
        agentPKs: this.agentMultiple,
        cmd: this.cmd,
        timeout: this.timeout,
        shell: this.shell,
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
        this.client = Object.keys(r.data)[0];
      });
    },
    getAgents() {
      this.$axios.get("/agents/listagentsnodetail/").then(r => {
        const ret = [];
        r.data.forEach(i => {
          ret.push({ label: i.hostname, value: i.pk });
        });
        this.agents = Object.freeze(ret);
      });
    },
  },
  created() {
    this.getTree();
    this.getAgents();
  },
};
</script>