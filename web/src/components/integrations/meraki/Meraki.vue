<template>
  <q-card flat>
    <q-tabs
      v-model="tab"
      dense
      align="left"
      class="text-grey"
      active-color="primary"
      indicator-color="primary"
      no-caps
      narrow-indicator
      inline-label
    >
      <q-tab
        icon="business"
        name="summary"
        label="Summary"
        clickable
        @click="tab = 'summary'"
        :active="tab === 'summary'"
        active-class="menu-link"
      />

      <q-btn-dropdown flat dense stretch no-caps icon="public" label="Networks" class="q-px-md">
        <q-list>
          <q-item v-for="network in networks" clickable>
            <q-item-section>{{ network.name }}</q-item-section>
            <q-item-section side>
              <q-icon name="keyboard_arrow_right" />
            </q-item-section>
            <q-menu fit square anchor="top right" self="top left">
              <q-item
                clickable
                v-close-popup
                @click="getNetworkApplicationTraffic(network.id)"
                :active="tab === network.id + 'networkTrafficAnalyticsTable'"
                active-class="menu-link"
              >Traffic analytics</q-item>
              <q-item
                clickable
                v-close-popup
                @click="getNetworkClientTraffic(network.id)"
                :active="tab === network.id + 'networkClientTrafficTable'"
                active-class="menu-link"
              >Clients</q-item>
              <q-item
                clickable
                v-close-popup
                @click="getNetworkEventsTable(network.id)"
                :active="tab === network.id + 'networkEventsTable'"
                active-class="menu-link"
              >Events</q-item>
            </q-menu>
          </q-item>
        </q-list>
      </q-btn-dropdown>
    </q-tabs>
    <q-tab-panels v-model="tab" animated>
      <q-tab-panel name="summary" class="q-px-md">
        <Summary :organizationID="organizationID" :organizationName="organizationName" />
      </q-tab-panel>
      <q-tab-panel :name="networkId + 'networkTrafficAnalyticsTable'">
        <NetworkTrafficAnalyticsTable
          :organizationID="organizationID"
          :organizationName="organizationName"
          :networkID="networkId"
          :networkName="networkName"
        />
      </q-tab-panel>
      <q-tab-panel :name="networkId + 'networkClientTrafficTable'">
        <NetworkClientsTrafficTable
          :organizationID="organizationID"
          :organizationName="organizationName"
          :networkID="networkId"
          :networkName="networkName"
        />
      </q-tab-panel>
      <q-tab-panel :name="networkId + 'networkEventsTable'">
        <NetworkEventsTable
          :organizationID="organizationID"
          :organizationName="organizationName"
          :networkID="networkId"
          :networkName="networkName"
        />
      </q-tab-panel>
    </q-tab-panels>
  </q-card>
</template>

<script>
import axios from "axios";
import AssociateOrg from "@/components/integrations/meraki/modals/AssociateOrg";
import Summary from "@/components/integrations/meraki/organization/Summary";
import NetworkTrafficAnalyticsTable from "@/components/integrations/meraki/traffic/NetworkTrafficAnalyticsTable";
import NetworkClientsTrafficTable from "@/components/integrations/meraki/traffic/NetworkClientsTrafficTable";
import NetworkEventsTable from "@/components/integrations/meraki/events/NetworkEventsTable";
// composable imports
import { ref, onBeforeMount, onMounted } from "vue";
import { useQuasar } from "quasar";
import { notifySuccess, notifyError } from "@/utils/notify";

export default {
  name: "ClientMeraki",
  props: ['node', 'integrations'],
  components: {
    AssociateOrg,
    Summary,
    NetworkTrafficAnalyticsTable,
    NetworkClientsTrafficTable,
    NetworkEventsTable,
  },
  setup(props) {
    const $q = useQuasar();

    const tab = ref("")
    const organization = ref([]);
    const networks = ref([]);
    const organizationID = ref("");
    const organizationName = ref("");
    const networkId = ref("");
    const networkName = ref("");

    function checkAssociation() {
      const obj = props.integrations[0].configuration.backend.associations.clients.find(o => o.node_id === props.node.id);

      if (obj) {
        getOrganization(obj)
      } else {
        $q.dialog({
          component: AssociateOrg,
        }).onOk(val => {
          let data = {
            associate_client: true,
            node_id: props.node.id,
            meraki_organization_id: parseInt(val['meraki_organization_id']),
            meraki_organization_label: val['meraki_organization_label']
          }
          axios
            .put(`/integrations/` + props.integrations[0].id + `/`, data)
            .then(r => {
              notifySuccess(val['meraki_organization_label'] + ' is now associated with ' + props.node.name)
              getOrganization(val)
            })
            .catch(e => {
              console.log(e)
            });
        })
      }
    }

    function getOrganization(obj) {
      $q.loading.show({ message: 'Getting ' + obj.meraki_organization_label + ' networks...' })
      axios
        .get(`/meraki/organizations/` + obj.meraki_organization_id)
        .then(r => {
          organizationID.value = r.data.id
          organizationName.value = r.data.name
          organization.value = r.data;
          if (r.data.errors) {
            notifyError(r.data.errors[0])
          }
          getNetworks()
        })
        .catch(e => {

        });
    }

    function getNetworks() {
      axios
        .get(`/meraki/` + organizationID.value + `/networks/`)
        .then(r => {
          networks.value = r.data;
          tab.value = 'summary'
          $q.loading.hide()
        })
        .catch(e => {
          console.log(e)
        });
    }

    function getNetworkApplicationTraffic(network_Id) {
      networkId.value = network_Id
      tab.value = this.networkId + "networkTrafficAnalyticsTable"
    }

    function getNetworkClientTraffic(network_Id) {
      networkId.value = network_Id
      tab.value = this.networkId + "networkClientTrafficTable"
    }

    function getNetworkEventsTable(network_Id) {
      networkId.value = network_Id
      tab.value = this.networkId + "networkEventsTable"
    }

    onMounted(() => {
      checkAssociation()

    })

    return {
      tab,
      splitterModel: ref(17),
      organization,
      networks,
      organizationID,
      organizationName,
      networkName,
      networkId,
      getNetworks,
      getNetworkApplicationTraffic,
      getNetworkClientTraffic,
      getNetworkEventsTable,
    };
  },
};
</script>
<style lang="sass">
.menu-link
  color: black
  background: #eeeeee
</style>