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
          <q-select
            label="Excluded Clients"
            dense
            options-dense
            outlined
            multiple
            v-model="localTemplate.excluded_clients"
            :options="clientOptions"
            use-chips
            map-options
            emit-value
          />
        </q-card-section>
        <q-card-section>
          <q-select
            label="Excluded Sites"
            dense
            options-dense
            outlined
            multiple
            v-model="localTemplate.excluded_sites"
            :options="siteOptions"
            use-chips
            map-options
            emit-value
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
        <q-card-section>
          <q-select
            label="Excluded Agents"
            dense
            options-dense
            outlined
            multiple
            v-model="localTemplate.excluded_agents"
            :options="agentOptions"
            use-chips
            map-options
            emit-value
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

        <q-card-section>
          <q-checkbox v-model="localTemplate.exclude_workstations" label="Exclude Workstations" />
          <q-checkbox v-model="localTemplate.exclude_servers" label="Exclude Servers" />
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
export default {
  name: "AlertExclusions",
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
      this.$axios
        .put(`alerts/templates/${this.template.id}/`, this.localTemplate)
        .then(r => {
          this.$q.loading.hide();
          this.onOk();
          this.notifySuccess("Alert Template exclusions added");
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
    this.localTemplate.id = this.template.id;
    this.localTemplate.excluded_clients = this.template.excluded_clients;
    this.localTemplate.excluded_sites = this.template.excluded_sites;
    this.localTemplate.excluded_agents = this.template.excluded_agents;
  },
};
</script>