<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row">
      <q-card-actions align="left">
        <div class="text-h6">Reset Agent Patch Policy</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section>
      <div class="text-subtitle3">
        Reset the patch policies for agents in a specific client or site.
        You can also leave the client and site blank to reset the patch policy for all agents.
        (This might take a while)
      </div>
      <q-form @submit.prevent="submit">
        <q-card-section>
          <q-select
            label="Clients"
            @clear="clearClient"
            clearable
            options-dense
            outlined
            v-model="client"
            :options="client_options"
          />
        </q-card-section>
        <q-card-section>
          <q-select
            :disabled="client === null"
            @clear="clearSite"
            label="Sites"
            clearable
            options-dense
            outlined
            v-model="site"
            :options="site_options"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn label="Reset Policies" color="primary" type="submit" />
          <q-btn label="Cancel" v-close-popup />
        </q-card-actions>
      </q-form>
    </q-card-section>
  </q-card>
</template>

<script>
import { notifySuccessConfig, notifyErrorConfig } from "@/mixins/mixins";

export default {
  name: "ResetPatchPolicy",
  data() {
    return {
      client: null,
      site: null,
      client_options: [],
    };
  },
  methods: {
    submit() {
      this.$q.loading.show();

      let data = {};

      if (this.client !== null) {
        data.client = this.client.label;
      }

      if (this.site !== null) {
        data.site = this.site.label;
      }

      this.$store
        .dispatch("automation/resetPatchPolicies", data)
        .then(r => {
          this.$q.loading.hide();
          this.$q.notify(notifySuccessConfig("The agent policies were reset successfully!"));
          this.$emit("close");
        })
        .catch(e => {
          this.$q.notify(notifyErrorConfig("There was an error reseting policies"));
        });
    },
    getClients() {
      this.$store
        .dispatch("loadClients")
        .then(r => {
          this.client_options = r.data.map(client => ({ label: client.client, value: client.id, sites: client.sites }));
        })
        .catch(e => {
          this.$q.notify(notifyErrorConfig("There was an error loading the clients!"));
        });
    },
    clearClient() {
      this.client = null;
      this.site = null;
    },
    clearSite() {
      this.site = null;
    },
  },
  computed: {
    site_options() {
      return !!this.client ? this.client.sites.map(site => ({ label: site.site, value: site.id })) : [];
    },
    buttonText() {
      return !!this.client ? "Clear Policies for ALL Agents" : "Clear Policies";
    },
  },
  mounted() {
    this.getClients();
  },
};
</script>