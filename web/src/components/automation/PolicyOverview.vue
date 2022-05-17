<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card class="q-dialog-plugin" style="width: 90vw; max-width: 90vw">
      <q-bar>
        <q-btn
          @click="getPolicyTree"
          class="q-mr-sm"
          dense
          flat
          push
          icon="refresh"
        />Policy Overview
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-splitter v-model="splitterModel" style="height: 600px">
        <template v-slot:before>
          <div class="q-pa-md">
            <q-tree
              ref="tree"
              :nodes="clientSiteTree"
              node-key="key"
              selected-color="primary"
              v-model:selected="selectedPolicyId"
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
              <PolicyChecksTab
                v-if="!!selectedPolicyId"
                :selectedPolicy="$refs.tree.getNodeByKey(selectedPolicyId).id"
              />
            </q-tab-panel>
            <q-tab-panel name="tasks">
              <PolicyAutomatedTasksTab
                v-if="!!selectedPolicyId"
                :selectedPolicy="$refs.tree.getNodeByKey(selectedPolicyId).id"
              />
            </q-tab-panel>
          </q-tab-panels>
        </template>
      </q-splitter>
    </q-card>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";
import PolicyChecksTab from "@/components/automation/PolicyChecksTab.vue";
import PolicyAutomatedTasksTab from "@/components/automation/PolicyAutomatedTasksTab.vue";

export default {
  name: "PolicyOverview",
  emits: ["hide", "ok", "cancel"],
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
        .then((r) => {
          this.processTreeDataFromApi(r.data);
          this.$q.loading.hide();
        })
        .catch(() => {
          this.$q.loading.hide();
        });
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

      for (let client of data) {
        var client_temp = {};

        client_temp["label"] = client.name;
        client_temp["id"] = unique_id;
        client_temp["icon"] = "business";
        client_temp["selectable"] = false;
        client_temp["children"] = [];
        client_temp["key"] = `${unique_id}${client.name}`;

        unique_id--;

        // Add any server policies assigned to client
        if (!!client.server_policy) {
          let disabled = "";

          // Indicate if the policy is active or not
          if (!client.server_policy.active) {
            disabled = " (disabled)";
          }

          const label = client.server_policy.name + " (Servers)" + disabled;
          client_temp["children"].push({
            label: label,
            icon: "policy",
            id: client.server_policy.id,
            key: `${client.server_policy.id}${label}`,
          });
        }

        // Add any workstation policies assigned to client
        if (!!client.workstation_policy) {
          let disabled = "";

          // Indicate if the policy is active or not
          if (!client.workstation_policy.active) {
            disabled = " (disabled)";
          }

          const label =
            client.workstation_policy.name + " (Workstations)" + disabled;
          client_temp["children"].push({
            label: label,
            icon: "policy",
            id: client.workstation_policy.id,
            key: `${client.workstation_policy.id}${label}`,
          });
        }

        // Iterate through Sites
        for (let site of client.sites) {
          var site_temp = {};
          site_temp["label"] = site.name;
          site_temp["id"] = unique_id;
          site_temp["icon"] = "apartment";
          site_temp["selectable"] = false;
          site_temp["key"] = `${unique_id}${site.name}`;

          unique_id--;

          // Add any server policies assigned to site
          if (!!site.server_policy) {
            site_temp["children"] = [];

            // Indicate if the policy is active or not
            let disabled = "";
            if (!site.server_policy.active) {
              disabled = " (disabled)";
            }

            const label = site.server_policy.name + " (Servers)" + disabled;
            site_temp["children"].push({
              label: label,
              icon: "policy",
              id: site.server_policy.id,
              key: `${site.server_policy.id}${label}`,
            });
          }

          // Add any server policies assigned to site
          if (!!site.workstation_policy) {
            site_temp["children"] = [];

            // Indicate if the policy is active or not
            let disabled = "";
            if (!site.workstation_policy.active) {
              disabled = " (disabled)";
            }

            const label =
              site.workstation_policy.name + " (Workstations)" + disabled;
            site_temp["children"].push({
              label: label,
              icon: "policy",
              id: site.workstation_policy.id,
              key: `${site.workstation_policy.id}${label}`,
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
