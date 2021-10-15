<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        {{ title }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
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

          <div class="text-h6">Custom Fields</div>
          <q-card-section v-for="field in customFields" :key="field.id">
            <CustomField v-model="custom_fields[field.name]" :field="field" />
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
import CustomField from "@/components/ui/CustomField";
import mixins from "@/mixins/mixins";
export default {
  name: "SitesForm",
  emits: ["hide", "ok", "cancel"],
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
        client: null,
        name: "",
      },
      custom_fields: {},
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
      const data = {
        site: this.localSite,
        custom_fields: this.formatCustomFields(this.customFields, this.custom_fields),
      };
      this.$axios
        .post("/clients/sites/", data)
        .then(r => {
          this.refreshDashboardTree();
          this.$q.loading.hide();
          this.onOk();
          this.notifySuccess(r.data);
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    editSite() {
      this.$q.loading.show();
      const data = {
        site: this.localSite,
        custom_fields: this.formatCustomFields(this.customFields, this.custom_fields),
      };
      this.$axios
        .put(`/clients/sites/${this.site.id}/`, data)
        .then(r => {
          this.refreshDashboardTree();
          this.onOk();
          this.$q.loading.hide();
          this.notifySuccess(r.data);
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    getSite() {
      this.$q.loading.show();
      this.$axios
        .get(`/clients/sites/${this.site.id}/`)
        .then(r => {
          this.$q.loading.hide();
          this.localSite.name = r.data.name;
          this.localSite.client = r.data.client;

          for (let field of this.customFields) {
            const value = r.data.custom_fields.find(value => value.field === field.id);

            if (field.type === "multiple") {
              if (value) this.custom_fields[field.name] = value.value;
              else this.custom_fields[field.name] = [];
            } else if (field.type === "checkbox") {
              if (value) this.custom_fields[field.name] = value.value;
              else this.this.custom_fields[field.name] = false;
            } else {
              if (value) this.custom_fields[field.name] = value.value;
              else this.custom_fields[field.name] = "";
            }
          }
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    refreshDashboardTree() {
      this.$store.dispatch("loadTree");
      this.$store.dispatch("getUpdatedSites");
    },
    getClients() {
      this.$axios
        .get("/clients/")
        .then(r => {
          r.data.forEach(client => {
            this.clientOptions.push({ label: client.name, value: client.id });
          });
        })
        .catch(e => {});
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
  mounted() {
    this.getClients();

    // Get custom fields
    this.getCustomFields("site").then(r => {
      this.customFields = r.data.filter(field => !field.hide_in_ui);
    });

    // Copy site prop locally
    if (this.editing) {
      this.getSite();
    } else {
      if (this.client) this.localSite.client = this.client;
    }
  },
};
</script>