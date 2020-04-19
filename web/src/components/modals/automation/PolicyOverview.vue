<template>
  <q-card style="width: 600px; max-width: 60vw">
    <q-bar>
      <q-btn @click="getPolicyTree" class="q-mr-sm" dense flat push icon="refresh" />Policy Overview
      <q-space />
      <q-btn dense flat icon="close" v-close-popup>
        <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
      </q-btn>
    </q-bar>
    <q-splitter
      v-model="splitterModel"
      style="height: 400px"
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
        <q-tab-panels
          v-model="selectedTab"
          animated
          transition-prev="jump-up"
          transition-next="jump-up"
        >
          <q-tab-panel name="Checks">
            <p>List Checks</p>
          </q-tab-panel>
          <q-tab-panel name="Tasks">
            <p>List Tasks</p>
          </q-tab-panel>
        </q-tab-panels>
      </template>
    </q-splitter>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";

export default {
  name: "PolicyOverview",
  mixins: [mixins],
  data () {
    return {
      splitterModel: 50,
      selected: "",
      selectedPolicy: {},
      selectedTab: "Checks",
      clientSiteTree: [],
    }
  },
  created() {
    this.getPolicyTree();
  },
  methods: {
    getPolicyTree() {
      axios.get(`/automation/policies/overview/`).then(r => {
        this.processTreeDataFromApi(r.data);
      })
      .catch(e => {
        this.$q.loading.hide();
        this.notifyError(e.response.data);
      });

    },
    loadPolicyDetails(key) {

      if (key === undefined) {return}

      let node = this.$refs.Tree.getNodeByKey(key);

      axios.get(`/automation/policies/${node.id}/`).then(r => {
        this.selectedPolicy = r.data
      })
      .catch(e => {
        this.$q.loading.hide();
        this.notifyError(e.response.data);
      });
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
  }
};
</script>