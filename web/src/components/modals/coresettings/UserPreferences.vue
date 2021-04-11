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
                <div class="col-4">Loading Bar Color:</div>
                <div class="col-4"></div>
                <q-select
                  outlined
                  dense
                  options-dense
                  v-model="loading_bar_color"
                  :options="loadingBarColors"
                  class="col-4"
                />
              </q-card-section>
              <q-card-section class="row">
                <div class="col-2">Client Sort:</div>
                <div class="col-2"></div>
                <q-select
                  map-options
                  emit-value
                  outlined
                  dense
                  options-dense
                  v-model="clientTreeSort"
                  :options="clientTreeSortOptions"
                  class="col-8"
                />
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
import { loadingBarColors } from "@/mixins/data";
import mixins from "@/mixins/mixins";

export default {
  name: "UserPreferences",
  mixins: [mixins],
  data() {
    return {
      loadingBarColors,
      agentDblClickAction: "",
      defaultAgentTblTab: "",
      clientTreeSort: "",
      tab: "ui",
      splitterModel: 20,
      loading_bar_color: "",
      clientTreeSortOptions: [
        {
          label: "Sort alphabetically, moving failing clients to the top",
          value: "alphafail",
        },
        {
          label: "Sort alphabetically only",
          value: "alpha",
        },
      ],
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
        this.clientTreeSort = r.data.client_tree_sort;
        this.loading_bar_color = r.data.loading_bar_color;
      });
    },
    editUserPrefs() {
      const data = {
        agent_dblclick_action: this.agentDblClickAction,
        default_agent_tbl_tab: this.defaultAgentTblTab,
        client_tree_sort: this.clientTreeSort,
        loading_bar_color: this.loading_bar_color,
      };
      this.$axios.patch("/accounts/users/ui/", data).then(r => {
        this.notifySuccess("Preferences were saved!");
        this.$emit("edited");
        this.$store.dispatch("loadTree");
        this.$emit("close");
      });
    },
  },
  created() {
    this.getUserPrefs();
  },
};
</script>