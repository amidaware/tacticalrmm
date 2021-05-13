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
                  @input="url_action = null"
                />
              </q-card-section>
              <q-card-section class="row" v-if="agentDblClickAction === 'urlaction'">
                <div class="col-6">URL Action:</div>
                <div class="col-2"></div>
                <q-select
                  map-options
                  emit-value
                  outlined
                  dense
                  options-dense
                  v-model="url_action"
                  :options="urlActions"
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
  emits: ["edit", "close"],
  mixins: [mixins],
  data() {
    return {
      loadingBarColors,
      agentDblClickAction: "",
      defaultAgentTblTab: "",
      clientTreeSort: "",
      url_action: null,
      tab: "ui",
      splitterModel: 20,
      loading_bar_color: "",
      urlActions: [],
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
        {
          label: "Run URL Action",
          value: "urlaction",
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
  watch: {
    agentDblClickAction(new_value, old_value) {
      if (new_value === "urlaction") {
        this.getURLActions();
      }
    },
  },
  methods: {
    getURLActions() {
      this.$axios
        .get("/core/urlaction/")
        .then(r => {
          if (r.data.length === 0) {
            this.notifyWarning("No URL Actions configured. Go to Settings > Global Settings > URL Actions");
            return;
          }
          this.urlActions = r.data.map(action => ({ label: action.name, value: action.id }));
        })
        .catch(() => {});
    },
    getUserPrefs() {
      this.$axios
        .get("/core/dashinfo/")
        .then(r => {
          this.agentDblClickAction = r.data.dbl_click_action;
          this.url_action = r.data.url_action;
          this.defaultAgentTblTab = r.data.default_agent_tbl_tab;
          this.clientTreeSort = r.data.client_tree_sort;
          this.loading_bar_color = r.data.loading_bar_color;
        })
        .catch(e => {});
    },
    editUserPrefs() {
      if (this.agentDblClickAction === "urlaction" && this.url_action === null) {
        this.notifyError("Select a URL Action");
        return;
      }
      const data = {
        agent_dblclick_action: this.agentDblClickAction,
        url_action: this.url_action,
        default_agent_tbl_tab: this.defaultAgentTblTab,
        client_tree_sort: this.clientTreeSort,
        loading_bar_color: this.loading_bar_color,
      };
      this.$axios
        .patch("/accounts/users/ui/", data)
        .then(r => {
          this.notifySuccess("Preferences were saved!");
          this.$emit("edit");
          this.$store.dispatch("loadTree");
          this.$emit("close");
        })
        .catch(e => {});
    },
  },
  created() {
    this.getUserPrefs();
  },
};
</script>