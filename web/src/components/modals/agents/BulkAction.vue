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
            <q-radio
              dense
              v-model="target"
              val="site"
              label="Site"
              @input="
                () => {
                  agentMultiple = [];
                  site = sites[0];
                }
              "
            />
            <q-radio dense v-model="target" val="agents" label="Selected Agents" />
            <q-radio dense v-model="target" val="all" label="All Agents" @input="agentMultiple = []" />
          </div>
        </div>
      </q-card-section>

      <q-card-section v-if="target === 'client' || target === 'site'">
        <q-select
          dense
          :rules="[val => !!val || '*Required']"
          outlined
          options-dense
          label="Select client"
          v-model="client"
          :options="client_options"
          @input="target === 'site' ? (site = sites[0]) : () => {}"
        />
      </q-card-section>

      <q-card-section v-if="target === 'site'">
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

      <q-card-section v-if="target === 'agents'">
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

      <q-card-section v-if="mode === 'script'">
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
      <q-card-section v-if="mode === 'script'">
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

      <q-card-section v-if="mode === 'command'">
        <p>Shell</p>
        <div class="q-gutter-sm">
          <q-radio dense v-model="shell" val="cmd" label="CMD" />
          <q-radio dense v-model="shell" val="powershell" label="Powershell" />
        </div>
      </q-card-section>
      <q-card-section v-if="mode === 'command'">
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

      <q-card-section v-if="mode === 'script' || mode === 'command'">
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

      <q-card-section v-if="mode === 'scan'">
        <div class="q-pa-none">
          <p>Action</p>
          <div class="q-gutter-sm">
            <q-radio dense v-model="selected_mode" val="scan" label="Run Patch Status Scan" />
            <q-radio dense v-model="selected_mode" val="install" label="Install Pending Patches Now" />
          </div>
        </div>
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
  props: {
    mode: !String,
  },
  data() {
    return {
      target: "client",
      selected_mode: null,
      scriptPK: null,
      timeout: 900,
      client: null,
      client_options: [],
      site: null,
      agents: [],
      agentMultiple: [],
      args: [],
      cmd: "",
      shell: "cmd",
    };
  },
  computed: {
    ...mapGetters(["scripts"]),
    sites() {
      return !!this.client ? this.formatSiteOptions(this.client.sites) : [];
    },
    scriptOptions() {
      const ret = this.scripts.map(script => ({ label: script.name, value: script.id }));
      return ret.sort((a, b) => a.label.localeCompare(b.label));
    },
  },
  methods: {
    send() {
      this.$q.loading.show();
      const data = {
        mode: this.selected_mode,
        target: this.target,
        site: this.site.value,
        client: this.client.value,
        agentPKs: this.agentMultiple,
        scriptPK: this.scriptPK,
        timeout: this.timeout,
        args: this.args,
        shell: "cmd",
        timeout: 300,
        cmd: null,
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
    getClients() {
      this.$axios.get("/clients/clients/").then(r => {
        this.client_options = this.formatClientOptions(r.data);

        this.client = this.client_options[0];
        this.site = this.sites[0];
      });
    },
    getAgents() {
      this.$axios.get("/agents/listagentsnodetail/").then(r => {
        const ret = r.data.map(agent => ({ label: agent.hostname, value: agent.pk }));
        this.agents = Object.freeze(ret.sort((a, b) => a.label.localeCompare(b.label)));
      });
    },
  },
  created() {
    this.getClients();
    this.getAgents();

    this.selected_mode = this.mode;
  },
};
</script>