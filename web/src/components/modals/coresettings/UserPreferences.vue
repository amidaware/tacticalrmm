<template>
  <q-card style="min-width: 85vh">
    <q-splitter v-model="splitterModel">
      <template v-slot:before>
        <q-tabs dense v-model="tab" vertical class="text-primary">
          <q-tab name="ui" label="User Interface" />
        </q-tabs>
      </template>
      <template v-slot:after>
        <q-form @submit.prevent="editUserPrefs">
          <q-card-section class="row items-center">
            <div class="text-h6">Preferences</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </q-card-section>
          <q-tab-panels v-model="tab" animated transition-prev="jump-up" transition-next="jump-up">
            <!-- UI -->
            <q-tab-panel name="ui">
              <div class="text-subtitle2">User Interface</div>
              <hr />
              <q-card-section class="row">
                <div class="col-6">Agent double-click action:</div>
                <div class="col-2"></div>
                <q-select
                  map-options
                  emit-value
                  outlined
                  dense
                  options-dense
                  v-model="agentDblClickAction"
                  :options="agentDblClickOptions"
                  class="col-4"
                />
              </q-card-section>
              <q-card-section class="row">
                <div class="col-6">Agent table default tab:</div>
                <div class="col-2"></div>
                <q-select
                  map-options
                  emit-value
                  outlined
                  dense
                  options-dense
                  v-model="defaultAgentTblTab"
                  :options="defaultAgentTblTabOptions"
                  class="col-4"
                />
              </q-card-section>
              <q-card-section class="row">
                <div class="col-6">Agent table default records per page:</div>
                <div class="col-2"></div>
                <q-input v-model.number="agentsPerPage" type="number" filled style="max-width: 100px" />
              </q-card-section>
            </q-tab-panel>
          </q-tab-panels>

          <q-card-section class="row items-center">
            <q-btn label="Save" color="primary" type="submit" />
          </q-card-section>
        </q-form>
      </template>
    </q-splitter>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "UserPreferences",
  mixins: [mixins],
  data() {
    return {
      agentDblClickAction: "",
      defaultAgentTblTab: "",
      agentsPerPage: 50,
      tab: "ui",
      splitterModel: 20,
      agentDblClickOptions: [
        {
          label: "Edit Agent",
          value: "editagent",
        },
        {
          label: "Take Control",
          value: "takecontrol",
        },
        {
          label: "Remote Background",
          value: "remotebg",
        },
      ],
      defaultAgentTblTabOptions: [
        {
          label: "Servers",
          value: "server",
        },
        {
          label: "Workstations",
          value: "workstation",
        },
        {
          label: "Mixed",
          value: "mixed",
        },
      ],
    };
  },
  methods: {
    getUserPrefs() {
      this.$axios.get("/core/dashinfo/").then(r => {
        this.agentDblClickAction = r.data.dbl_click_action;
        this.defaultAgentTblTab = r.data.default_agent_tbl_tab;
        this.agentsPerPage = r.data.agents_per_page;
      });
    },
    editUserPrefs() {
      const data = {
        userui: true,
        agent_dblclick_action: this.agentDblClickAction,
        default_agent_tbl_tab: this.defaultAgentTblTab,
        agents_per_page: this.agentsPerPage,
      };
      this.$axios.patch("/accounts/users/ui/", data).then(r => {
        this.notifySuccess("Preferences were saved!");
        this.$emit("edited");
        this.$emit("refresh");
        this.$emit("close");
      });
    },
  },
  created() {
    this.getUserPrefs();
  },
};
</script>