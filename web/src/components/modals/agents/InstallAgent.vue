<template>
  <q-card style="min-width: 35vw">
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
        <q-card-section class="q-gutter-sm">
          <q-select
            outlined
            dense
            options-dense
            label="Client"
            v-model="client"
            :options="client_options"
            @update:model-value="site = sites[0]"
          />
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-select dense options-dense outlined label="Site" v-model="site" :options="sites" />
        </q-card-section>
        <q-card-section>
          <div class="q-gutter-sm">
            <q-radio v-model="agenttype" val="server" label="Server" @update:model-value="power = false" />
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
              style="max-width: 200px"
              stack-label
            />
          </div>
        </q-card-section>
        <q-card-section>
          <div class="q-gutter-sm">
            <q-checkbox v-model="rdp" dense label="Enable RDP" />
            <q-checkbox v-model="ping" dense label="Enable Ping">
              <q-tooltip> Enable ICMP echo requests in the local firewall </q-tooltip>
            </q-checkbox>
            <q-checkbox v-model="power" dense v-show="agenttype === 'workstation'" label="Disable sleep/hibernate" />
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
import mixins from "@/mixins/mixins";
import AgentDownload from "@/components/modals/agents/AgentDownload";
import { getBaseUrl } from "@/boot/axios";

export default {
  name: "InstallAgent",
  mixins: [mixins],
  components: { AgentDownload },
  props: {
    sitepk: Number,
  },
  data() {
    return {
      client_options: [],
      client: null,
      site: null,
      agenttype: "server",
      expires: 24,
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
    getClients() {
      this.$q.loading.show();
      this.$axios
        .get("/clients/clients/")
        .then(r => {
          this.client_options = this.formatClientOptions(r.data);
          if (this.sitepk !== undefined && this.sitepk !== null) {
            this.client_options.forEach(client => {
              let site = client.sites.find(site => site.id === this.sitepk);

              if (site !== undefined) {
                this.client = client;
                this.site = { value: site.id, label: site.name };
              }
            });
          } else {
            this.client = this.client_options[0];
            this.site = this.sites[0];
          }
          this.$q.loading.hide();
        })
        .catch(() => {
          this.$q.loading.hide();
        });
    },
    addAgent() {
      const api = getBaseUrl();
      const clientStripped = this.client.label
        .replace(/\s/g, "")
        .toLowerCase()
        .replace(/([^a-zA-Z0-9]+)/g, "");
      const siteStripped = this.site.label
        .replace(/\s/g, "")
        .toLowerCase()
        .replace(/([^a-zA-Z0-9]+)/g, "");

      const fileName =
        this.arch === "64"
          ? `rmm-${clientStripped}-${siteStripped}-${this.agenttype}.exe`
          : `rmm-${clientStripped}-${siteStripped}-${this.agenttype}-x86.exe`;

      const data = {
        installMethod: this.installMethod,
        client: this.client.value,
        site: this.site.value,
        expires: this.expires,
        agenttype: this.agenttype,
        power: this.power ? 1 : 0,
        rdp: this.rdp ? 1 : 0,
        ping: this.ping ? 1 : 0,
        arch: this.arch,
        api,
        fileName,
      };

      if (this.installMethod === "manual") {
        this.$axios
          .post("/agents/installer/", data)
          .then(r => {
            this.info = {
              expires: this.expires,
              data: r.data,
              arch: this.arch,
            };
            this.showAgentDownload = true;
          })
          .catch(e => {});
      } else if (this.installMethod === "exe") {
        this.$q.loading.show({ message: "Generating executable..." });

        this.$axios
          .post("/agents/installer/", data, { responseType: "blob" })
          .then(r => {
            this.$q.loading.hide();
            const blob = new Blob([r.data], { type: "application/vnd.microsoft.portable-executable" });
            let link = document.createElement("a");
            link.href = window.URL.createObjectURL(blob);
            link.download = fileName;
            link.click();
            this.showDLMessage();
          })
          .catch(() => {
            this.$q.loading.hide();
          });
      } else if (this.installMethod === "powershell") {
        const psName = `rmm-${clientStripped}-${siteStripped}-${this.agenttype}.ps1`;
        this.$axios
          .post("/agents/installer/", data, { responseType: "blob" })
          .then(({ data }) => {
            const blob = new Blob([data], { type: "text/plain" });
            let link = document.createElement("a");
            link.href = window.URL.createObjectURL(blob);
            link.download = psName;
            link.click();
            this.showDLMessage();
          })
          .catch(e => {});
      }
    },
    showDLMessage() {
      this.$q.dialog({
        message: `Installer for ${this.client.label}, ${this.site.label} (${this.agenttype}) will now be downloaded.
              You may reuse this installer for ${this.expires} hours before it expires. No command line arguments are needed.`,
      });
    },
  },
  computed: {
    sites() {
      return !!this.client ? this.formatSiteOptions(this.client.sites) : [];
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
  mounted() {
    this.getClients();
  },
};
</script>