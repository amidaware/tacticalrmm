<template>
  <div>
    <div class="row">
      <div class="text-subtitle2">Custom Fields</div>
      <q-space />
      <q-btn
        size="sm"
        color="grey-5"
        icon="fas fa-plus"
        text-color="black"
        label="Add custom field"
        @click="addCustomField"
      />
    </div>
    <hr />
    <div>
      <q-tabs
        v-model="tab"
        dense
        inline-label
        class="text-grey"
        active-color="primary"
        indicator-color="primary"
        align="left"
        narrow-indicator
        no-caps
      >
        <q-tab name="client" label="Clients" />
        <q-tab name="site" label="Sites" />
        <q-tab name="agent" label="Agents" />
      </q-tabs>

      <q-separator />
      <q-scroll-area :thumb-style="thumbStyle" style="height: 50vh">
        <q-tab-panels v-model="tab" :animated="false">
          <q-tab-panel name="client">
            <CustomFieldsTable @refresh="getCustomFields" :data="clientFields" />
          </q-tab-panel>

          <q-tab-panel name="site">
            <CustomFieldsTable @refresh="getCustomFields" :data="siteFields" />
          </q-tab-panel>

          <q-tab-panel name="agent">
            <CustomFieldsTable @refresh="getCustomFields" :data="agentFields" />
          </q-tab-panel>
        </q-tab-panels>
      </q-scroll-area>
    </div>
  </div>
</template>

<script>
import CustomFieldsTable from "@/components/modals/coresettings/CustomFieldsTable";
import CustomFieldsForm from "@/components/modals/coresettings/CustomFieldsForm";

export default {
  name: "CustomFields",
  components: {
    CustomFieldsTable,
  },
  data() {
    return {
      tab: "client",
      customFields: [],
      thumbStyle: {
        right: "2px",
        borderRadius: "5px",
        backgroundColor: "#027be3",
        width: "5px",
        opacity: 0.75,
      },
    };
  },
  computed: {
    agentFields() {
      return this.customFields.filter(field => field.model === "agent");
    },
    siteFields() {
      return this.customFields.filter(field => field.model === "site");
    },
    clientFields() {
      return this.customFields.filter(field => field.model === "client");
    },
  },
  methods: {
    getCustomFields() {
      this.$q.loading.show();

      this.$axios
        .get(`/core/customfields/`)
        .then(r => {
          this.$q.loading.hide();
          this.customFields = r.data;
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    addCustomField() {
      this.$q
        .dialog({
          component: CustomFieldsForm,
          componentProps: {
            model: this.tab,
          },
        })
        .onOk(() => {
          this.getCustomFields();
        });
    },
  },
  mounted() {
    this.getCustomFields();
  },
};
</script>