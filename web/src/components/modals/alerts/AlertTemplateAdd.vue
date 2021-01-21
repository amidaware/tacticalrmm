<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        Edit Alert Template assigned to {{ type }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form @submit.prevent="submit" ref="form">
        <q-card-section v-if="options.length > 0">
          <q-select
            v-model="selectedTemplate"
            :options="options"
            outlined
            dense
            clearable
            emit-value
            map-options
            :label="capitalize(type) + ' Alert Template'"
          >
          </q-select>
        </q-card-section>
        <q-card-section v-else> No Alert Templates have been setup. Go to Settings > Alerts Manager </q-card-section>
        <q-card-actions align="right">
          <q-btn dense flat label="Cancel" v-close-popup />
          <q-btn v-if="options.length > 0" flat label="Submit" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "AlertTemplateAdd",
  props: {
    object: !Object,
    type: {
      required: true,
      type: String,
      validator: function (value) {
        // The value must match one of these strings
        return ["site", "client", "policy"].includes(value);
      },
    },
  },
  mixins: [mixins],
  data() {
    return {
      selectedTemplate: null,
      options: [],
    };
  },
  methods: {
    submit() {
      // close because nothing was edited
      if (this.object.alertTemplate === this.selectedTemplate) {
        this.hide();
        return;
      }

      this.$q.loading.show();

      const data = {
        id: this.object.id,
        alert_template: this.selectedTemplate,
      };

      let url = "";
      if (this.type === "client") url = `/clients/${this.object.id}/client/`;
      else if (this.type === "site") url = `/clients/${this.object.id}/site/`;
      else if (this.type === "policy") url = `/automation/${this.object.id}/policy/`;

      const text = this.selectedTemplate ? "assigned" : "removed";
      this.$axios
        .put(url, data)
        .then(r => {
          this.$q.loading.hide();
          this.onOk();
          this.notifySuccess(`Alert Template ${text} successfully!`);
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError("Something went wrong!");
        });
    },
    getAlertTemplates() {
      this.$q.loading.show();
      this.$axios
        .get("/alerts/alerttemplates")
        .then(r => {
          this.options = r.data.map(template => ({
            label: template.name,
            value: template.id,
          }));
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError("Add error occured while loading alert templates");
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
  mounted() {
    this.getAlertTemplates();
    this.selectedTemplate = this.object.alertTemplate;
  },
};
</script>