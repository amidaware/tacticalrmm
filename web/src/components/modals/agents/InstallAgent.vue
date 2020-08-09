<template>
  <div>
    <q-card style="min-width: 25vw" v-if="loaded">
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
          <q-card-section v-if="tree !== null">
            <q-select
              outlined
              label="Client"
              v-model="client"
              :options="Object.keys(tree)"
              @input="site = sites[0]"
            />
          </q-card-section>
          <q-card-section>
            <q-select outlined label="Site" v-model="site" :options="sites" />
          </q-card-section>
          <q-card-section>
            <div>
              Agent type:
              <br />
              <q-radio v-model="agenttype" val="server" label="Server" />
              <q-radio v-model="agenttype" val="workstation" label="Workstation" />
            </div>
          </q-card-section>
          <q-card-section>
            Select Version
            <q-select outlined v-model="version" :options="Object.values(versions)" />
          </q-card-section>
          <q-card-actions align="left">
            <q-btn label="Generate Agent" color="primary" type="submit" />
          </q-card-actions>
        </q-form>
      </q-card-section>
    </q-card>
    <div>
      <q-dialog v-model="showAgentDownload">
        <AgentDownload :info="info" @close="showAgentDownload = false" />
      </q-dialog>
    </div>
  </div>
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

      const data = { client: this.client, site: this.site };
      axios.post("/agents/installagent/", data).then((r) => {
        this.info = { exe, download, api, agenttype: this.agenttype, data: r.data };
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