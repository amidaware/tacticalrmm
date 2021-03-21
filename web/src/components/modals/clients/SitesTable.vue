<template>
  <q-dialog ref="dialog" @hide="onHide">
    <div class="q-dialog-plugin" style="width: 60vw; max-width: 60vw">
      <q-card>
        <q-bar>
          <q-btn @click="getSites" class="q-mr-sm" dense flat push icon="refresh" />Sites for {{ client.name }}
          <q-space />
          <q-btn dense flat icon="close" v-close-popup>
            <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
          </q-btn>
        </q-bar>
        <div class="q-pa-sm" style="min-height: 40vh; max-height: 40vh">
          <div class="q-gutter-sm">
            <q-btn label="New" dense flat push unelevated no-caps icon="add" @click="showAddSite" />
          </div>
          <q-table
            dense
            :data="sites"
            :columns="columns"
            :pagination.sync="pagination"
            row-key="id"
            binary-state-sort
            hide-pagination
            virtual-scroll
            :rows-per-page-options="[0]"
            no-data-label="No Sites"
          >
            <!-- body slots -->
            <template v-slot:body="props">
              <q-tr :props="props" class="cursor-pointer" @dblclick="showEditSite(props.row)">
                <!-- context menu -->
                <q-menu context-menu>
                  <q-list dense style="min-width: 200px">
                    <q-item clickable v-close-popup @click="showEditSite(props.row)">
                      <q-item-section side>
                        <q-icon name="edit" />
                      </q-item-section>
                      <q-item-section>Edit</q-item-section>
                    </q-item>
                    <q-item clickable v-close-popup @click="showSiteDeleteModal(props.row)">
                      <q-item-section side>
                        <q-icon name="delete" />
                      </q-item-section>
                      <q-item-section>Delete</q-item-section>
                    </q-item>

                    <q-separator></q-separator>

                    <q-item clickable v-close-popup>
                      <q-item-section>Close</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
                <!-- name -->
                <q-td>
                  {{ props.row.name }}
                </q-td>
              </q-tr>
            </template>
          </q-table>
        </div>
      </q-card>
    </div>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";
import SitesForm from "@/components/modals/clients/SitesForm";
import DeleteClient from "@/components/modals/clients/DeleteClient";

export default {
  name: "SitesTable",
  mixins: [mixins],
  props: {
    client: !Object,
  },
  data() {
    return {
      sites: [],
      columns: [{ name: "name", label: "Name", field: "name", align: "left" }],
      pagination: {
        rowsPerPage: 0,
        sortBy: "name",
        descending: true,
      },
    };
  },
  methods: {
    getSites() {
      this.$q.loading.show();
      this.$axios
        .get(`clients/${this.client.id}/client/`)
        .then(r => {
          this.sites = r.data.sites;
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError("Unable to get Sites.");
        });
    },
    showSiteDeleteModal(site) {
      this.$q
        .dialog({
          component: DeleteClient,
          parent: this,
          object: site,
          type: "site",
        })
        .onOk(() => {
          this.getSites();
        });
    },
    showEditSite(site) {
      this.$q
        .dialog({
          component: SitesForm,
          parent: this,
          site: site,
          client: site.client,
        })
        .onOk(() => {
          this.getSites();
        });
    },
    showAddSite() {
      this.$q
        .dialog({
          component: SitesForm,
          parent: this,
          client: this.client.id,
        })
        .onOk(() => {
          this.getSites();
        });
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
  },
  mounted() {
    this.getSites();
  },
};
</script>