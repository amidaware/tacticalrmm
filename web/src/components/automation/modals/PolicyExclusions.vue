<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card style="width: 50vw; max-width: 50vw">
      <q-bar>
        Policy Exclusions for {{ policy.name }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form ref="form" @submit.prevent="onSubmit">
        <q-card-section>
          <tactical-dropdown
            v-model="localPolicy.excluded_clients"
            :options="clientOptions"
            label="Excluded Clients"
            outlined
            multiple
            mapOptions
          />
        </q-card-section>
        <q-card-section>
          <tactical-dropdown
            v-model="localPolicy.excluded_sites"
            :options="siteOptions"
            label="Excluded Sites"
            outlined
            multiple
            mapOptions
          />
        </q-card-section>
        <q-card-section>
          <tactical-dropdown
            v-model="localPolicy.excluded_agents"
            :options="agentOptions"
            label="Excluded Agents"
            outlined
            multiple
            mapOptions
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
import TacticalDropdown from "@/components/ui/TacticalDropdown";
import mixins from "@/mixins/mixins";
export default {
  name: "PolicyExclusions",
  components: { TacticalDropdown },
  emits: ["hide", "ok", "cancel"],
  props: { policy: !Object },
  mixins: [mixins],
  data() {
    return {
      localPolicy: {
        excluded_clients: [],
        excluded_sites: [],
        excluded_agents: [],
      },
      clientOptions: [],
      siteOptions: [],
      agentOptions: [],
    };
  },
  methods: {
    onSubmit() {
      this.$axios
        .put(`automation/policies/${this.policy.id}/`, this.localPolicy)
        .then(r => {
          this.$q.loading.hide();
          this.onOk();
          this.notifySuccess("Policy exclusions added");
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    getClients() {
      this.$axios
        .get("/clients/")
        .then(r => {
          this.clientOptions = r.data.map(client => ({ label: client.name, value: client.id }));
        })
        .catch(e => {});
    },
    getSites() {
      this.$axios
        .get("/clients/")
        .then(r => {
          r.data.forEach(client => {
            this.siteOptions.push({ category: client.name });
            client.sites.forEach(site => this.siteOptions.push({ label: site.name, value: site.id }));
          });
        })
        .catch(e => {});
    },
    getOptions() {
      this.getClients();
      this.getSites();
      this.getAgentOptions().then(options => (this.agentOptions = Object.freeze(options)));
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
    this.getOptions();

    // copy prop data locally
    this.localPolicy.id = this.policy.id;
    this.localPolicy.excluded_clients = this.policy.excluded_clients.map(client => client.id);
    this.localPolicy.excluded_sites = this.policy.excluded_sites.map(site => site.id);
    this.localPolicy.excluded_agents = this.policy.excluded_agents.map(agent => agent.pk);
  },
};
</script>