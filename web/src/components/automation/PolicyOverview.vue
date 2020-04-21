<template>
  <q-card style="width: 900px; max-width: 90vw">
    <q-bar>
      <q-btn @click="getPolicyTree" class="q-mr-sm" dense flat push icon="refresh" />Policy Overview
      <q-space />
      <q-btn dense flat icon="close" v-close-popup>
        <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
      </q-btn>
    </q-bar>
    <q-splitter
      v-model="splitterModel"
      style="height: 600px"
    >
      <template v-slot:before>
        <div class="q-pa-md">
          <q-tree
            ref="Tree"
            :nodes="clientSiteTree"
            node-key="label"
            :selected.sync="selected"
            selected-color="primary"
            @update:selected="loadPolicyDetails"
            default-expand-all
          >

          </q-tree>
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
            <template v-if="Object.keys(selectedPolicy).length === 0">
              <p>Select a Policy</p>
            </template>
            <OverviewChecksTab v-else :policypk="policypk" />
          </q-tab-panel>
          <q-tab-panel name="tasks">
            <template v-if="Object.keys(selectedPolicy).length === 0">
              <p>Select a Policy</p>
            </template>
            <OverviewAutomatedTasksTab v-else :policypk="policypk" />
          </q-tab-panel>
        </q-tab-panels>
      </template>
    </q-splitter>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
import OverviewChecksTab from "@/components/automation/OverviewChecksTab"
import OverviewAutomatedTasksTab from "@/components/automation/OverviewAutomatedTasksTab"

export default {
  name: "PolicyOverview",
  components: {
    OverviewChecksTab,
    OverviewAutomatedTasksTab,
  },
  mixins: [mixins],
  data () {
    return {
      splitterModel: 25,
      selected: "",
      selectedPolicy: {},
      selectedTab: "checks",
      clientSiteTree: [],
    }
  },
  mounted () {
    this.getPolicyTree();
  },
  methods: {
    getPolicyTree () {
      axios.get(`/automation/policies/overview/`).then(r => {
        this.processTreeDataFromApi(r.data);
      })
      .catch(e => {
        this.$q.loading.hide();
        this.notifyError(e.response.data);
      });

    },
    loadPolicyDetails (key) {
      if (key === undefined) {return;}
      this.selectedPolicy = this.$refs.Tree.getNodeByKey(key);
    },
    processTreeDataFromApi(data) {
      /* Structure
       * [{
       *   "client_name_1": {
       *     "policies": [
       *       {
       *         id: 1
       *         name: "Policy Name 1"
       *       }
       *     ]
       *     "site_name_1": {
       *       "policies": []
       *     }
       *   }
       * }]
      */ 

      var result = [];

      for (let client in data) {

        var client_temp = {};

        client_temp["label"] = client;
        client_temp["icon"] = "business";
        client_temp["selectable"] = false;
        client_temp["children"] = [];

        // Add any policies assigned to client
        if (data[client].policies.length > 0) {
          for (let policy in data[client].policies)
            client_temp["children"].push({
              label: data[client].policies[policy].name,
              icon: 'policy',
              id: data[client].policies[policy].id
            });
        }

        // Iterate through Sites
        for (let site in data[client].sites) {
          var site_temp = {}
          site_temp["label"] = site;
          site_temp["icon"] = "apartment";
          site_temp["selectable"] = false;
          
          // Add any policies assigned to site
          if (data[client].sites[site].policies.length > 0) {

            site_temp["children"] = [];

            for (let policy in data[client].sites[site].policies) {
              site_temp["children"].push({
                label: data[client].sites[site].policies[policy].name,
                icon: 'policy',
                id: data[client].sites[site].policies[policy].id
              });
            }
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
  computed: {
    policypk () {
      return this.selectedPolicy.id;
    }
  }
};
</script>