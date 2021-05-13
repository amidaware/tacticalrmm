<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card class="q-dialog-plugin">
      <q-bar>
        Delete {{ object.name }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form @submit="submit">
        <q-card-section>
          <q-select
            label="Site to move agents to"
            dense
            options-dense
            outlined
            v-model="selectedSite"
            :options="siteOptions"
            map-options
            emit-value
            :rules="[val => !!val || 'Select the site that the agents should be moved to']"
          >
            <template v-slot:option="scope">
              <q-item
                v-if="!scope.opt.category"
                v-bind="scope.itemProps"
                v-on="scope.itemProps.itemEvents"
                class="q-pl-lg"
              >
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
        <q-card-actions align="right">
          <q-btn dense flat label="Cancel" v-close-popup />
          <q-btn dense flat label="Delete" color="negative" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";
export default {
  name: "DeleteClient",
  emits: ["hide", "ok", "cancel"],
  mixins: [mixins],
  props: {
    object: !Object,
    type: !String,
  },
  data() {
    return {
      siteOptions: [],
      selectedSite: null,
      agentCount: 0,
    };
  },
  methods: {
    submit() {
      if (this.type === "client") this.deleteClient();
      else this.deleteSite();
    },
    deleteClient() {
      this.$q
        .dialog({
          title: "Are you sure?",
          message: `Delete client ${this.object.name}. Agents from all sites will be moved to the selected site`,
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$q.loading.show();
          this.$axios
            .delete(`/clients/${this.object.id}/${this.selectedSite}/`)
            .then(r => {
              this.refreshDashboardTree();
              this.$q.loading.hide();
              this.onOk();
              this.notifySuccess(r.data);
            })
            .catch(e => {
              this.$q.loading.hide();
            });
        });
    },
    deleteSite() {
      this.$q
        .dialog({
          title: "Are you sure?",
          message: `Delete site ${this.object.name}. Agents from all sites will be moved to the selected site`,
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$q.loading.show();
          this.$axios
            .delete(`/clients/sites/${this.object.id}/${this.selectedSite}/`)
            .then(r => {
              this.refreshDashboardTree();
              this.$q.loading.hide();
              this.onOk();
              this.notifySuccess(r.data);
            })
            .catch(e => {
              this.$q.loading.hide();
            });
        });
    },
    getSites() {
      this.$axios
        .get("/clients/clients/")
        .then(r => {
          this.agentCount = this.getAgentCount(r.data, this.type, this.object.id);
          r.data.forEach(client => {
            // remove client that is being deleted from options
            if (this.type === "client") {
              if (client.id !== this.object.id) {
                this.siteOptions.push({ category: client.name });

                client.sites.forEach(site => {
                  this.siteOptions.push({ label: site.name, value: site.id });
                });
              }
            } else {
              this.siteOptions.push({ category: client.name });

              client.sites.forEach(site => {
                if (site.id !== this.object.id) {
                  this.siteOptions.push({ label: site.name, value: site.id });
                } else if (client.sites.length === 1) {
                  this.siteOptions.pop();
                }
              });
            }
          });
        })
        .catch(e => {});
    },
    refreshDashboardTree() {
      this.$store.dispatch("loadTree");
      this.$store.dispatch("getUpdatedSites");
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
    this.getSites();
  },
};
</script>