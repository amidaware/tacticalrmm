<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card class="q-dialog-plugin" style="width: 900px; max-width: 90vw">
      <q-bar>
        <q-btn @click="getPolicyTree" class="q-mr-sm" dense flat push icon="refresh" />Policy Overview
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-splitter v-model="splitterModel" style="height: 600px">
        <template v-slot:before>
          <div class="q-pa-md">
            <q-tree
              ref="tree"
              :nodes="clientSiteTree"
              node-key="id"
              selected-color="primary"
              @update:selected="setSelectedPolicyId(key)"
              default-expand-all
            ></q-tree>
          </div>
        </template>

        <template v-slot:after>
          <q-tabs
            v-model="selectedTab"
            dense
            inline-label
            class="text-grey"
            active-color="primary"
            indicator-color="primary"
            align="left"
            narrow-indicator
            no-caps
          >
            <q-tab name="checks" icon="fas fa-check-double" label="Checks" />
            <q-tab name="tasks" icon="fas fa-tasks" label="Tasks" />
          </q-tabs>
          <q-tab-panels v-model="selectedTab" animated transition-prev="jump-up" transition-next="jump-up">
            <q-tab-panel name="checks">
              <PolicyChecksTab :selectedPolicy="selectedPolicyId" />
            </q-tab-panel>
            <q-tab-panel name="tasks">
              <PolicyAutomatedTasksTab :selectedPolicy="selectedPolicyId" />
            </q-tab-panel>
          </q-tab-panels>
        </template>
      </q-splitter>
    </q-card>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";
import PolicyChecksTab from "@/components/automation/PolicyChecksTab";
import PolicyAutomatedTasksTab from "@/components/automation/PolicyAutomatedTasksTab";

export default {
  name: "PolicyOverview",
  components: {
    PolicyAutomatedTasksTab,
    PolicyChecksTab,
  },
  mixins: [mixins],
  data() {
    return {
      splitterModel: 25,
      selectedPolicyId: null,
      selectedTab: "checks",
      clientSiteTree: [],
    };
  },
  methods: {
    getPolicyTree() {
      this.$q.loading.show();
      this.$axios
        .get("/automation/policies/overview/")
        .then(r => {
          this.processTreeDataFromApi(r.data);
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError("Error getting policy tree data");
        });
    },
    setSelectedPolicyId(key) {
      if (!key) {
        return;
      }
      this.selectedPolicyId = this.$refs.tree.getNodeByKey(key);
    },
    processTreeDataFromApi(data) {
      /* Structure
       * [{
       *   client: Client Name 1,
       *   policy: {
       *     id: 1,
       *     name: "Policy Name 1"
       *   },
       *   sites: [{
       *     name: "Site Name 1",
       *     policy: {
       *       id: 2,
       *       name: "Policy Name 2"
       *     }
       *   }]
       * }]
       */

      var result = [];

      // Used by tree for unique identification
      let unique_id = 0;

      for (let client in data) {
        var client_temp = {};

        client_temp["label"] = data[client].name;
        client_temp["id"] = unique_id;
        client_temp["icon"] = "business";
        client_temp["selectable"] = false;
        client_temp["children"] = [];

        unique_id--;

        // Add any server policies assigned to client
        if (data[client].server_policy !== null) {
          let disabled = "";

          // Indicate if the policy is active or not
          if (!data[client].server_policy.active) {
            disabled = " (disabled)";
          }

          client_temp["children"].push({
            label: data[client].server_policy.name + " (Servers)" + disabled,
            icon: "policy",
            id: data[client].server_policy.id,
          });
        }

        // Add any workstation policies assigned to client
        if (data[client].workstation_policy !== null) {
          let disabled = "";

          // Indicate if the policy is active or not
          if (!data[client].workstation_policy.active) {
            disabled = " (disabled)";
          }

          client_temp["children"].push({
            label: data[client].workstation_policy.name + " (Workstations)" + disabled,
            icon: "policy",
            id: data[client].workstation_policy.id,
          });
        }

        // Iterate through Sites
        for (let site in data[client].sites) {
          var site_temp = {};
          site_temp["label"] = data[client].sites[site].name;
          site_temp["id"] = unique_id;
          site_temp["icon"] = "apartment";
          site_temp["selectable"] = false;

          unique_id--;

          // Add any server policies assigned to site
          if (data[client].sites[site].server_policy !== null) {
            site_temp["children"] = [];

            // Indicate if the policy is active or not
            let disabled = "";
            if (!data[client].sites[site].server_policy.active) {
              disabled = " (disabled)";
            }

            site_temp["children"].push({
              label: data[client].sites[site].server_policy.name + " (Servers)" + disabled,
              icon: "policy",
              id: data[client].sites[site].server_policy.id,
            });
          }

          // Add any server policies assigned to site
          if (data[client].sites[site].workstation_policy !== null) {
            site_temp["children"] = [];

            // Indicate if the policy is active or not
            let disabled = "";
            if (!data[client].sites[site].workstation_policy.active) {
              disabled = " (disabled)";
            }

            site_temp["children"].push({
              label: data[client].sites[site].workstation_policy.name + " (Workstations)" + disabled,
              icon: "policy",
              id: data[client].sites[site].workstation_policy.id,
            });
          }

          // Add Site to Client children array
          client_temp.children.push(site_temp);
        }

        // Add Client and it's Sites to result array
        result.push(client_temp);
      }

      this.clientSiteTree = result;
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
    this.getPolicyTree();
  },
};
</script>
