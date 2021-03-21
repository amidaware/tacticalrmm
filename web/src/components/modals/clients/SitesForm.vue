<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        {{ title }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-card-section>
        <q-form @submit.prevent="submit">
          <q-card-section>
            <q-select
              v-model="localSite.client"
              label="Client"
              :options="clientOptions"
              outlined
              dense
              options-dense
              map-options
              emit-value
              :rules="[val => !!val || 'Client is required']"
            />
          </q-card-section>
          <q-card-section>
            <q-input
              :rules="[val => !!val || 'Name is required']"
              outlined
              dense
              v-model="localSite.name"
              label="Name"
            />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn dense flat label="Cancel" v-close-popup />
            <q-btn dense flat label="Save" color="primary" type="submit" />
          </q-card-actions>
        </q-form>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script>
import CustomField from "@/components/CustomField";
import mixins from "@/mixins/mixins";
export default {
  name: "ClientsForm",
  components: {
    CustomField,
  },
  mixins: [mixins],
  props: {
    site: !Object,
    client: !Number,
  },
  data() {
    return {
      customFields: [],
      clientOptions: [],
      localSite: {
        id: null,
        client: null,
        name: "",
      },
    };
  },
  computed: {
    title() {
      return this.editing ? "Edit Site" : "Add Site";
    },
    editing() {
      return !!this.site;
    },
  },
  methods: {
    submit() {
      if (!this.editing) this.addSite();
      else this.editSite();
    },
    addSite() {
      this.$q.loading.show();
      this.$axios
        .post("/clients/sites/", this.localSite)
        .then(r => {
          this.refreshDashboardTree();
          this.$q.loading.hide();
          this.onOk();
          this.notifySuccess(r.data);
        })
        .catch(e => {
          this.$q.loading.hide();
          if (e.response.data.name) {
            this.notifyError(e.response.data.name);
          } else {
            this.notifyError(e.response.data);
          }
        });
    },
    editSite() {
      this.$q.loading.show();
      this.$axios
        .put(`/clients/sites/${this.site.id}/`, this.localSite)
        .then(r => {
          this.refreshDashboardTree();
          this.onOk();
          this.$q.loading.hide();
          this.notifySuccess(r.data);
        })
        .catch(e => {
          this.$q.loading.hide();
          if (e.response.data.name) {
            this.notifyError(e.response.data.name);
          } else {
            this.notifyError(e.response.data);
          }
        });
    },
    refreshDashboardTree() {
      this.$store.dispatch("loadTree");
      this.$store.dispatch("getUpdatedSites");
    },
    getClients() {
      this.$axios.get("/clients/clients/").then(r => {
        r.data.forEach(client => {
          this.clientOptions.push({ label: client.name, value: client.id });
        });
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
    onOk() {
      this.$emit("ok");
      this.hide();
    },
  },
  created() {
    this.getClients();

    // Copy site prop locally
    if (this.editing) {
      this.localSite.id = this.site.id;
      this.localSite.name = this.site.name;
      this.localSite.client = this.site.client;
    }

    if (this.client) this.localSite.client = this.client;
  },
};
</script>