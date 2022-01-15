<template>
  <q-splitter v-model="splitterModel">
    <template v-slot:before>
      <q-inner-loading :showing="menuLoading" color="primary" />
      <q-expansion-item group="organizationsGroup" icon="business" caption="Organization" :label="organization.name"
        @click="getNetworks(organization.id, organization.name)">
        <q-list>
          <q-item clickable v-ripple active-class="menu-link"
            :active="menuItem === organizationID + 'organizationOverview'" :inset-level="1" @click="getOverview()">
            <q-item-section>Overview</q-item-section>
          </q-item>
          <q-item clickable v-ripple active-class="menu-link" :active="menuItem === organizationID + 'topClients'"
            :inset-level="1" @click="getTopClients()">
            <q-item-section>Top clients</q-item-section>
          </q-item>

        </q-list>
        <q-expansion-item group="networksGroup" v-for="network in networks" v-bind:key="network.id" expand-separator
          clickable icon="public" header-:inset-level="1" :label="network.name" caption="Network">
          <q-list>
            <q-item :inset-level="1" clickable active-class="menu-link" :active="menu === network.id + 'traffic'">
              <q-item-section>Traffic</q-item-section>
              <q-item-section side>
                <q-icon name="keyboard_arrow_right" />
              </q-item-section>
              <q-menu fit square anchor="top right" self="top left">
                <q-item clickable v-close-popup active-class="menu-link"
                  :active="menuItem === network.id + 'applicationTraffic'" @click="getNetwork(network.id, network.name);
                    getNetworkApplicationTraffic(network.id)">
                  Applications
                </q-item>
                <q-item clickable v-close-popup active-class="menu-link"
                  :active="menuItem === network.id + 'clientTraffic'" @click="getNetwork(network.id, network.name);
                    getNetworkClientTraffic(network.id)">
                  Clients
                </q-item>
              </q-menu>
            </q-item>
            <q-item clickable :inset-level="1" v-ripple :active="menuItem === network.id + 'networkEventsTable'" @click="
            getNetwork(network.id, network.name);
            getNetworkEventsTable(network.id);
          " active-class="menu-link">
              <q-item-section>Events</q-item-section>
            </q-item>
          </q-list>
        </q-expansion-item>
      </q-expansion-item>
    </template>
    <template v-slot:after>
      <q-tab-panels v-model="menuItem" animated vertical transition-prev="jump-up" transition-next="jump-up">
        <q-tab-panel :name="organizationID + 'organizationOverview'" v-if="show">
          <Overview :organizationID="organizationID" :organizationName="organizationName" />
        </q-tab-panel>

        <q-tab-panel :name="organizationID + 'topClients'">
          <TopClientsTable :organizationID="organizationID" :organizationName="organizationName" />
        </q-tab-panel>

        <q-tab-panel :name="networkID + 'applicationTraffic'">
          <NetworkApplicationTrafficTable :organizationID="organizationID" :organizationName="organizationName"
            :networkID="networkID" :networkName="networkName" />
        </q-tab-panel>

        <q-tab-panel :name="networkID + 'clientTraffic'">
          <NetworkClientsTrafficTable :organizationID="organizationID" :organizationName="organizationName"
            :networkID="networkID" :networkName="networkName" />
        </q-tab-panel>
        <q-tab-panel :name="networkID + 'networkEventsTable'">
          <NetworkEventsTable :organizationID="organizationID" :organizationName="organizationName"
            :networkID="networkID" :networkName="networkName" />
        </q-tab-panel>
      </q-tab-panels>
    </template>
  </q-splitter>
</template>

<script>
  import axios from "axios";
  import AssociateOrg from "@/components/integrations/meraki/modals/AssociateOrg";

  import Overview from "@/components/integrations/meraki/organization/Overview";
  import TopClientsTable from "@/components/integrations/meraki/organization/TopClientsTable";
  import NetworkApplicationTrafficTable from "@/components/integrations/meraki/traffic/NetworkApplicationTrafficTable";
  import NetworkClientsTrafficTable from "@/components/integrations/meraki/traffic/NetworkClientsTrafficTable";
  import NetworkEventsTable from "@/components/integrations/meraki/events/NetworkEventsTable";
  // composable imports
  import { ref, computed, onMounted, onBeforeMount } from "vue";
  import { useMeta, useQuasar, useDialogPluginComponent } from "quasar";
  import { notifySuccess, notifyError } from "@/utils/notify";

  export default {
    name: "ClientMeraki",
    emits: [...useDialogPluginComponent.emits],
    components: {
      AssociateOrg,
      Overview,
      TopClientsTable,
      NetworkApplicationTrafficTable,
      NetworkClientsTrafficTable,
      NetworkEventsTable,
    },
    setup(props) {
      const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
      const $q = useQuasar();

      let organization = ref([]);
      let networks = ref([]);
      let organizationID = ref("");
      let organizationName = ref("");
      let networkID = ref("");
      let networkName = ref("");
      let menu = ref("");
      let menuItem = ref("");
      let menuLoading = ref(false);

      function getOrganization() {
        $q.dialog({
          component: AssociateOrg,
          componentProps: {

          }
        }).onOk(val => {
          $q.loading.show({ message: 'Applying organization...' })
          axios
            .get(`/meraki/organizations/` + val['organization'].value)
            .then(r => {
              organizationID.value = val['organization'].value
              organization.value = r.data;
              if (r.data.errors) {
                notifyError(r.data.errors[0])
              }
              $q.loading.hide()
            })
            .catch(e => {
            });
        })
      }

      function getNetworks() {
        menuLoading.value = true;
        axios
          .get(`/meraki/` + organizationID.value + `/networks/`)
          .then(r => {
            networks.value = r.data;
            menuLoading.value = false;
          })
          .catch(e => { });
      }
      function getOverview() {
        menu.value = organizationID.value + "organizationOverview";
        menuItem.value = organizationID.value + "organizationOverview";
      }

      function getTopClients() {
        menu.value = organizationID.value + "topClients";
        menuItem.value = organizationID.value + "topClients";
      }

      function getNetwork(netID, netName) {
        networkID.value = netID;
        networkName.value = netName;
      }

      function getNetworkApplicationTraffic() {
        menu.value = networkID.value + "traffic";
        menuItem.value = networkID.value + "applicationTraffic";
      }

      function getNetworkClientTraffic() {
        menu.value = networkID.value + "traffic";
        menuItem.value = networkID.value + "clientTraffic";
      }

      function getNetworkEventsTable() {
        menu.value = networkID.value + "networkEvents";
        menuItem.value = networkID.value + "networkEventsTable";
      }

      onMounted(() => {
        // getOrganization();
      });

      onBeforeMount(() => {
        getOrganization()
      })

      return {
        splitterModel: ref(17),
        menuLoading,
        menu,
        menuItem,
        organization,
        networks,
        organizationID,
        organizationName,
        networkName,
        networkID,
        getOverview,
        getNetworks,
        getNetwork,
        getTopClients,
        getNetworkApplicationTraffic,
        getNetworkClientTraffic,
        getNetworkEventsTable,
        // quasar dialog plugin
        dialogRef,
        onDialogHide,
      };
    },
  };
</script>