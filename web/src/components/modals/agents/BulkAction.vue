<template>
  <q-card style="min-width: 50vw">
    <q-card-section class="row items-center">
      <div class="text-h6">
        {{ modalTitle }}
        <div v-if="modalCaption !== null" class="text-caption">{{ modalCaption }}</div>
      </div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
      <br />
    </q-card-section>
    <q-form @submit.prevent="send">
      <q-card-section>
        <div class="q-pa-none">
          <p>Agent Type</p>
          <div class="q-gutter-sm">
            <q-radio dense v-model="monType" val="all" label="All" />
            <q-radio dense v-model="monType" val="servers" label="Servers" />
            <q-radio dense v-model="monType" val="workstations" label="Workstations" />
          </div>
        </div>
      </q-card-section>
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

      <q-card-section v-if="target === 'client' || target === 'site'" class="q-pb-none">
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
        <q-select
          v-if="target === 'site'"
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

      <q-card-section v-if="mode === 'script'" class="q-pt-none">
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
          @input="setScriptDefaults"
        >
          <template v-slot:option="scope">
            <q-item v-if="!scope.opt.category" v-bind="scope.itemProps" class="q-pl-lg">
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
      <q-card-section v-if="mode === 'script'" class="q-pt-none">
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
          :rules="[val => !!val || '*Required', val => val >= 5 || 'Minimum is 5 seconds']"
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
import { mapState } from "vuex";
import mixins from "@/mixins/mixins";

export default {
  name: "BulkAction",
  emits: ["close"],
  mixins: [mixins],
  props: {
    mode: !String,
  },
  data() {
    return {
      target: "client",
      monType: "all",
      selected_mode: null,
      scriptOptions: [],
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
      modalTitle: null,
      modalCaption: null,
    };
  },
  computed: {
    ...mapState(["showCommunityScripts"]),
    sites() {
      return !!this.client ? this.formatSiteOptions(this.client.sites) : [];
    },
  },
  methods: {
    setScriptDefaults() {
      const script = this.scriptOptions.find(i => i.value === this.scriptPK);

      this.timeout = script.timeout;
      this.args = script.args;
    },
    send() {
      this.$q.loading.show();
      const data = {
        mode: this.selected_mode,
        monType: this.monType,
        target: this.target,
        site: this.site.value,
        client: this.client.value,
        agentPKs: this.agentMultiple,
        scriptPK: this.scriptPK,
        timeout: this.timeout,
        args: this.args,
        shell: this.shell,
        timeout: this.timeout,
        cmd: this.cmd,
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
        });
    },
    getClients() {
      this.$axios
        .get("/clients/clients/")
        .then(r => {
          this.client_options = this.formatClientOptions(r.data);

          this.client = this.client_options[0];
          this.site = this.sites[0];
        })
        .catch(e => {});
    },
    getAgents() {
      this.$axios
        .get("/agents/listagentsnodetail/")
        .then(r => {
          const ret = r.data.map(agent => ({ label: agent.hostname, value: agent.pk }));
          this.agents = Object.freeze(ret.sort((a, b) => a.label.localeCompare(b.label)));
        })
        .catch(e => {});
    },
    setTitles() {
      switch (this.mode) {
        case "command":
          this.modalTitle = "Run Bulk Command";
          this.modalCaption = "Run a shell command on multiple agents in parallel";
          break;
        case "script":
          this.modalTitle = "Run Bulk Script";
          this.modalCaption = "Run a script on multiple agents in parallel";
          break;
        case "scan":
          this.modalTitle = "Bulk Patch Management";
          break;
      }
    },
  },
  mounted() {
    this.setTitles();
    this.getClients();
    this.getAgents();
    this.getScriptOptions(this.showCommunityScripts).then(options => (this.scriptOptions = Object.freeze(options)));

    this.selected_mode = this.mode;
  },
};
</script>