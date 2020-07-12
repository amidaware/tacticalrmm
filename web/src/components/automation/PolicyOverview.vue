<template>
  <q-card style="width: 900px; max-width: 90vw">
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
            :selected.sync="selected"
            selected-color="primary"
            @update:selected="loadPolicyDetails"
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
        <q-tab-panels
          v-model="selectedTab"
          animated
          transition-prev="jump-up"
          transition-next="jump-up"
        >
          <q-tab-panel name="checks">
            <PolicyChecksTab />
          </q-tab-panel>
          <q-tab-panel name="tasks">
            <PolicyAutomatedTasksTab />
          </q-tab-panel>
        </q-tab-panels>
      </template>
    </q-splitter>
  </q-card>
</template>

<script>
import mixins, { notifyErrorConfig } from "@/mixins/mixins";
import PolicyChecksTab from "@/components/automation/PolicyChecksTab";
import PolicyAutomatedTasksTab from "@/components/automation/PolicyAutomatedTasksTab";

export default {
  name: "PolicyOverview",
  components: {
    PolicyAutomatedTasksTab,
    PolicyChecksTab
  },
  mixins: [mixins],
  data() {
    return {
      splitterModel: 25,
      selected: "",
      selectedPolicy: {},
      selectedTab: "checks",
      clientSiteTree: []
    };
  },
  methods: {
    getPolicyTree() {
      this.$q.loading.show();
      this.$store
        .dispatch("automation/loadPolicyTreeData")
        .then(r => {
          this.processTreeDataFromApi(r.data);
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
          this.$q.notify(notifyErrorConfig(e.response.data));
        });
    },
    loadPolicyDetails(key) {
      if (key === undefined || key === null) {
        return;
      }

      this.selectedPolicy = this.$refs.tree.getNodeByKey(key);

      this.$store.dispatch("automation/loadPolicyChecks", this.selectedPolicy.id);
      this.$store.commit("automation/setSelectedPolicy", this.selectedPolicy.id);
      this.$store.dispatch("automation/loadPolicyAutomatedTasks", this.selectedPolicy.id);
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

        client_temp["label"] = data[client].client;
        client_temp["id"] = unique_id;
        client_temp["icon"] = "business";
        client_temp["selectable"] = false;
        client_temp["children"] = [];

        unique_id--;

        // Add any policies assigned to client

        if (data[client].policy !== null) {
          let disabled = "";

          // Indicate if the policy is active or not
          if (!data[client].policy.active) {
            disabled = " (disabled)";
          }

          client_temp["children"].push({
            label: data[client].policy.name + disabled,
            icon: "policy",
            id: data[client].policy.id
          });
        }

        // Iterate through Sites
        for (let site in data[client].sites) {
          var site_temp = {};
          site_temp["label"] = data[client].sites[site].site;
          site_temp["id"] = unique_id;
          site_temp["icon"] = "apartment";
          site_temp["selectable"] = false;

          unique_id--;

          // Add any policies assigned to site
          if (data[client].sites[site].policy !== null) {
            site_temp["children"] = [];

            // Indicate if the policy is active or not
            let disabled = "";
            if (!data[client].sites[site].policy.active) {
              disabled = " (disabled)";
            }

            site_temp["children"].push({
              label: data[client].sites[site].policy.name + disabled,
              icon: "policy",
              id: data[client].sites[site].policy.id
            });
          }

          // Add Site to Client children array
          client_temp.children.push(site_temp);
        }

        // Add Client and it's Sites to result array
        result.push(client_temp);
      }

      this.clientSiteTree = result;
    }
  },
  mounted() {
    this.getPolicyTree();
  }
};
</script>
