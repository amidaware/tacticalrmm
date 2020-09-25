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
            options-dense
            label="Client"
            v-model="client"
            :options="Object.keys(tree)"
            @input="site = sites[0]"
          />
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-select dense options-dense outlined label="Site" v-model="site" :options="sites" />
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
          OS
          <div class="q-gutter-sm">
            <q-radio v-model="arch" val="64" label="64 bit" />
            <q-radio v-model="arch" val="32" label="32 bit" />
          </div>
        </q-card-section>
        <q-card-section>
          Installation Method
          <div class="q-gutter-sm">
            <q-radio v-model="installMethod" val="exe" label="Dynamically generated exe" />
            <q-radio v-model="installMethod" val="powershell" label="Powershell" />
            <q-radio v-model="installMethod" val="manual" label="Manual" />
          </div>
        </q-card-section>
        <q-card-actions align="left">
          <q-btn :label="installButtonText" color="primary" type="submit" />
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
      client: null,
      site: null,
      agenttype: "server",
      expires: 720,
      power: false,
      rdp: false,
      ping: false,
      showAgentDownload: false,
      info: {},
      installMethod: "exe",
      arch: "64",
    };
  },
  methods: {
    getClientsSites() {
      this.$q.loading.show();
      axios
        .get("/clients/loadclients/")
        .then(r => {
          this.tree = r.data;
          this.client = Object.keys(r.data)[0];
          this.loaded = true;
          this.$q.loading.hide();
        })
        .catch(() => {
          this.notifyError("Something went wrong");
          this.$q.loading.hide();
        });
    },
    addAgent() {
      const api = axios.defaults.baseURL;
      const clientStripped = this.client
        .replace(/\s/g, "")
        .toLowerCase()
        .replace(/([^a-zA-Z0-9]+)/g, "");
      const siteStripped = this.site
        .replace(/\s/g, "")
        .toLowerCase()
        .replace(/([^a-zA-Z0-9]+)/g, "");

      const data = {
        installMethod: this.installMethod,
        client: this.client,
        site: this.site,
        expires: this.expires,
        agenttype: this.agenttype,
        power: this.power ? 1 : 0,
        rdp: this.rdp ? 1 : 0,
        ping: this.ping ? 1 : 0,
        arch: this.arch,
        api,
      };

      if (this.installMethod === "manual") {
        this.$axios
          .post("/agents/installagent/", data)
          .then(r => {
            this.info = {
              expires: this.expires,
              data: r.data,
              arch: this.arch,
            };
            this.showAgentDownload = true;
          })
          .catch(e => {
            let err;
            switch (e.response.status) {
              case 406:
                err = "Missing 64 bit meshagent.exe. Upload it from File > Upload Mesh Agent";
                break;
              case 415:
                err = "Missing 32 bit meshagent-x86.exe. Upload it from File > Upload Mesh Agent";
                break;
              default:
                err = "Something went wrong";
            }
            this.notifyError(err, 4000);
          });
      } else if (this.installMethod === "exe") {
        this.$q.loading.show({ message: "Generating executable..." });

        const fileName =
          this.arch === "64"
            ? `rmm-${clientStripped}-${siteStripped}-${this.agenttype}.exe`
            : `rmm-${clientStripped}-${siteStripped}-${this.agenttype}-x86.exe`;
        this.$axios
          .post("/agents/installagent/", data, { responseType: "blob" })
          .then(r => {
            this.$q.loading.hide();
            const blob = new Blob([r.data], { type: "application/vnd.microsoft.portable-executable" });
            let link = document.createElement("a");
            link.href = window.URL.createObjectURL(blob);
            link.download = fileName;
            link.click();
            this.showDLMessage();
          })
          .catch(e => {
            let err;
            switch (e.response.status) {
              case 409:
                err = "Golang is not installed";
                break;
              case 412:
                err = "Golang build failed. Check debug log for the error message";
                break;
              case 406:
                err = "Missing 64 bit meshagent.exe. Upload it from File > Upload Mesh Agent";
                break;
              case 415:
                err = "Missing 32 bit meshagent-x86.exe. Upload it from File > Upload Mesh Agent";
                break;
              default:
                err = "Something went wrong";
            }
            this.$q.loading.hide();
            this.notifyError(err, 4000);
          });
      } else if (this.installMethod === "powershell") {
        const psName = `rmm-${clientStripped}-${siteStripped}-${this.agenttype}.ps1`;
        this.$axios
          .post("/agents/installagent/", data, { responseType: "blob" })
          .then(({ data }) => {
            const blob = new Blob([data], { type: "text/plain" });
            let link = document.createElement("a");
            link.href = window.URL.createObjectURL(blob);
            link.download = psName;
            link.click();
            this.showDLMessage();
          })
          .catch(e => {
            let err;
            switch (e.response.status) {
              case 406:
                err = "Missing 64 bit meshagent.exe. Upload it from File > Upload Mesh Agent";
                break;
              case 415:
                err = "Missing 32 bit meshagent-x86.exe. Upload it from File > Upload Mesh Agent";
                break;
              default:
                err = "Something went wrong";
            }
            this.notifyError(err, 4000);
          });
      }
    },
    showDLMessage() {
      this.$q.dialog({
        message: `Installer for ${this.client}, ${this.site} (${this.agenttype}) will now be downloaded.
              You may reuse this installer for ${this.expires} hours before it expires. No command line arguments are needed.`,
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
    installButtonText() {
      let text;
      switch (this.installMethod) {
        case "exe":
          text = "Generate and download exe";
          break;
        case "powershell":
          text = "Download powershell script";
          break;
        case "manual":
          text = "Show manual installation instructions";
          break;
      }

      return text;
    },
  },
  created() {
    this.getClientsSites();
  },
};
</script>