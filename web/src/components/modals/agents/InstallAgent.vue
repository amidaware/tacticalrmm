<template>
  <q-card style="min-width: 35vw" v-if="loaded">
    <q-card-section class="row">
      <q-card-actions align="left">
        <div class="text-h6">Add an agent</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section>
      <q-form @submit.prevent="addAgent">
        <q-card-section v-if="tree !== null" class="q-gutter-sm">
          <q-select
            outlined
            dense
            label="Client"
            v-model="client"
            :options="Object.keys(tree)"
            @input="site = sites[0]"
          />
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-select dense outlined label="Site" v-model="site" :options="sites" />
        </q-card-section>
        <q-card-section>
          <div class="q-gutter-sm">
            <q-radio v-model="agenttype" val="server" label="Server" @input="power = false" />
            <q-radio v-model="agenttype" val="workstation" label="Workstation" />
          </div>
        </q-card-section>
        <q-card-section>
          <div class="q-gutter-sm">
            <q-input
              v-model.number="expires"
              dense
              type="number"
              filled
              label="Token expiration (hours)"
              style="max-width: 200px;"
              stack-label
            />
          </div>
        </q-card-section>
        <q-card-section>
          <div class="q-gutter-sm">
            <q-checkbox v-model="rdp" dense label="Enable RDP" />
            <q-checkbox v-model="ping" dense label="Enable Ping" />
            <q-checkbox
              v-model="power"
              dense
              v-show="agenttype === 'workstation'"
              label="Disable sleep/hibernate"
            />
          </div>
        </q-card-section>
        <q-card-section>
          Select Version
          <q-select dense outlined v-model="version" :options="Object.values(versions)" />
        </q-card-section>
        <q-card-actions align="left">
          <q-btn label="Show Install Command" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card-section>
    <q-dialog v-model="showAgentDownload">
      <AgentDownload :info="info" @close="showAgentDownload = false" />
    </q-dialog>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
import AgentDownload from "@/components/modals/agents/AgentDownload";

export default {
  name: "InstallAgent",
  mixins: [mixins],
  components: { AgentDownload },
  data() {
    return {
      loaded: false,
      tree: {},
      versions: {},
      client: null,
      site: null,
      version: null,
      agenttype: "server",
      expires: 1,
      power: false,
      rdp: false,
      ping: false,
      github: [],
      showAgentDownload: false,
      info: {},
    };
  },
  methods: {
    getClientsSites() {
      this.$q.loading.show();
      axios
        .get("/clients/loadclients/")
        .then((r) => {
          this.tree = r.data;
          this.client = Object.keys(r.data)[0];
          axios
            .get("/agents/getagentversions/")
            .then((r) => {
              this.versions = r.data.versions;
              this.version = Object.values(r.data.versions)[0];
              this.github = r.data.github;
              this.loaded = true;
              this.$q.loading.hide();
            })
            .catch(() => {
              this.notifyError("Something went wrong");
              this.$q.loading.hide();
            });
        })
        .catch(() => {
          this.notifyError("Something went wrong");
          this.$q.loading.hide();
        });
    },
    addAgent() {
      const api = axios.defaults.baseURL;
      const release = this.github.filter((i) => i.name === this.version)[0];
      const download = release.assets[0].browser_download_url;
      const exe = `${release.name}.exe`;

      const data = { client: this.client, site: this.site, expires: this.expires };
      axios.post("/agents/installagent/", data).then((r) => {
        this.info = {
          exe,
          download,
          api,
          agenttype: this.agenttype,
          expires: this.expires,
          power: this.power ? 1 : 0,
          rdp: this.rdp ? 1 : 0,
          ping: this.ping ? 1 : 0,
          data: r.data,
        };
        this.showAgentDownload = true;
      });
    },
  },
  computed: {
    sites() {
      if (this.tree !== null && this.client !== null) {
        this.site = this.tree[this.client][0];
        return this.tree[this.client];
      }
    },
  },
  created() {
    this.getClientsSites();
  },
};
</script>