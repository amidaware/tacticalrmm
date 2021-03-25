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
            <q-input
              outlined
              dense
              v-model="localClient.name"
              label="Name"
              :rules="[val => (val && val.length > 0) || '*Required']"
            />
          </q-card-section>
          <q-card-section v-if="!editing">
            <q-input
              :rules="[val => !!val || '*Required']"
              outlined
              dense
              v-model="site.name"
              label="Default first site"
            />
          </q-card-section>

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
import CustomField from "@/components/CustomField";
import mixins from "@/mixins/mixins";
export default {
  name: "ClientsForm",
  components: {
    CustomField,
  },
  mixins: [mixins],
  props: {
    client: !Object,
  },
  data() {
    return {
      customFields: [],
      site: {
        name: "",
      },
      localClient: {
        name: "",
      },
      custom_fields: {},
    };
  },
  computed: {
    title() {
      return this.editing ? "Edit Client" : "Add Client";
    },
    editing() {
      return !!this.client;
    },
  },
  methods: {
    submit() {
      if (!this.editing) this.addClient();
      else this.editClient();
    },
    addClient() {
      this.$q.loading.show();
      this.$axios
        .post("/clients/clients/", {
          site: this.site,
          client: this.localClient,
        })
        .then(r => {
          this.saveCustomFields();
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
    editClient() {
      this.$q.loading.show();

      this.$axios
        .put(`/clients/${this.client.id}/client/`, this.localClient)
        .then(r => {
          this.saveCustomFields(this.client.id);
          this.refreshDashboardTree();
          this.onOk();
          this.$q.loading.hide();
          this.notifySuccess(r.data);
        })
        .catch(e => {
          this.$q.loading.hide();
          console.log({ e });
          if (e.response.data.name) {
            this.notifyError(e.response.data.name);
          } else {
            this.notifyError(e.response.data);
          }
        });
    },
    getClient() {
      this.$q.loading.show();
      this.$axios
        .get(`/clients/${this.client.id}/client/`)
        .then(r => {
          this.$q.loading.hide();
          this.localClient.name = r.data.name;

          for (let field of this.customFields) {
            const value = r.data.custom_fields.find(value => value.field === field.id);

            if (!!value) this.$set(this.custom_fields, field.name, value.value);
            else if (!!field.default_value) this.$set(this.custom_fields, field.name, field.default_value);
            else this.$set(this.custom_fields, field.name, "");
          }
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    saveCustomFields(pk = None) {
      this.$axios
        .post(`/clients/customfields/`, {
          custom_fields: this.formatCustomFields(this.customFields, this.custom_fields, pk),
        })
        .catch(e => {
          console.log({ e });
        });
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
    // Get custom fields
    this.getCustomFields("client").then(r => {
      this.customFields = r.data;
    });

    // Copy client prop locally
    if (this.editing) {
      this.getClient();
    }
  },
};
</script>