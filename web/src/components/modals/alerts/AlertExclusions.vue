<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card style="width: 50vw; max-width: 50vw">
      <q-bar>
        Alert Exclusions for {{ template.name }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form ref="form" @submit.prevent="onSubmit">
        <q-card-section>
          <tactical-dropdown
            label="Excluded Clients"
            outlined
            multiple
            v-model="localTemplate.excluded_clients"
            :options="clientOptions"
            use-chips
            mapOptions
            filterable
          />
        </q-card-section>
        <q-card-section>
          <tactical-dropdown
            label="Excluded Sites"
            outlined
            multiple
            v-model="localTemplate.excluded_sites"
            :options="siteOptions"
            use-chips
            mapOptions
            filterable
          />
        </q-card-section>
        <q-card-section>
          <tactical-dropdown
            label="Excluded Agents"
            outlined
            multiple
            v-model="localTemplate.excluded_agents"
            :options="agentOptions"
            use-chips
            mapOptions
            filterable
          />
        </q-card-section>

        <q-card-section>
          <q-checkbox
            v-model="localTemplate.exclude_workstations"
            label="Exclude Workstations"
          />
          <q-checkbox
            v-model="localTemplate.exclude_servers"
            label="Exclude Servers"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn dense flat label="Cancel" v-close-popup />
          <q-btn dense flat label="Save" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";
import TacticalDropdown from "@/components/ui/TacticalDropdown";
export default {
  name: "AlertExclusions",
  components: {
    TacticalDropdown,
  },
  emits: ["hide", "ok"],
  props: { template: !Object },
  mixins: [mixins],
  data() {
    return {
      localTemplate: {
        excluded_clients: [],
        excluded_sites: [],
        excluded_agents: [],
        exclude_servers: false,
        exclude_workstations: false,
      },
      clientOptions: [],
      siteOptions: [],
      agentOptions: [],
    };
  },
  methods: {
    onSubmit() {
      this.$q.loading.show();
      this.$axios
        .put(`alerts/templates/${this.template.id}/`, this.localTemplate)
        .then(() => {
          this.$q.loading.hide();
          this.onOk();
          this.notifySuccess("Alert Template exclusions added");
        })
        .catch(() => {
          this.$q.loading.hide();
        });
    },
    getClientsandSites() {
      this.$q.loading.show();
      this.$axios
        .get("/clients/")
        .then((r) => {
          this.clientOptions = r.data.map((client) => ({
            label: client.name,
            value: client.id,
          }));

          r.data.forEach((client) => {
            this.siteOptions.push({ category: client.name });
            client.sites.forEach((site) =>
              this.siteOptions.push({ label: site.name, value: site.id })
            );
          });
          this.$q.loading.hide();
        })
        .catch(() => {
          this.$q.loading.hide();
        });
    },
    getOptions() {
      this.getAgentOptions("id").then(
        (options) => (this.agentOptions = Object.freeze(options))
      );
      this.getClientsandSites();
    },
    show() {
      this.$refs.dialog.show();
    },
    hide() {
      this.$refs.dialog.hide();
    },
    onHide() {
      this.$emit("hide");
    },
    onOk() {
      this.$emit("ok");
      this.hide();
    },
  },
  created() {
    // copy prop data locally
    this.localTemplate.id = this.template.id;
    this.localTemplate.excluded_clients = this.template.excluded_clients;
    this.localTemplate.excluded_sites = this.template.excluded_sites;
    this.localTemplate.excluded_agents = this.template.excluded_agents;
    this.localTemplate.exclude_servers = this.template.exclude_servers;
    this.localTemplate.exclude_workstations =
      this.template.exclude_workstations;
    this.getOptions();
  },
};
</script>
