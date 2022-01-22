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
        <q-card flat class="q-mb-sm">
          <q-btn-dropdown label="Actions" flat>
            <q-list>
              <q-item clickable v-close-popup @click="changeAssociation()" disable>
                <q-item-section>
                  <q-item-label>Change Association</q-item-label>
                </q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="removeOrgAssociation()">
                <q-item-section>
                  <q-item-label>Remove Association</q-item-label>
                </q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="checkAssociation()">
                <q-item-section>
                  <q-item-label>Refresh</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-btn-dropdown>

          <q-scroll-area style="height: 245px;">
            <div class="q-py-md row justify-center q-gutter-md">
              <q-card flat bordered class="my-card bg-grey-1 q-mx-md" v-for="device in uplinks">
                <q-card-section>
                  <div class="text-h6">{{ device.model }}</div>
                  <div class="text-caption">{{ device.serial }}</div>
                </q-card-section>
                <q-card-section>
                  <div v-for="uplink in device.uplinks">
                    <span v-if="uplink.ip">
                      {{ uplink.interface }} - {{ uplink.ip }}
                      <q-icon
                        v-if="uplink.status == 'active' || uplink.status == 'ready'"
                        name="brightness_1"
                        color="positive"
                      />
                      <q-icon v-else name="brightness_1" color="negative" />
                    </span>
                    <span v-else>
                      {{ uplink.interface }}
                      <q-icon
                        v-if="uplink.status == 'active' || uplink.status == 'ready'"
                        name="brightness_1"
                        color="positive"
                      />
                      <q-icon v-else name="brightness_1" color="negative" />
                    </span>
                  </div>
                </q-card-section>
                <q-separator />
                <q-card-section
                  class="text-caption text-weight-light"
                >Reported at: {{ device.lastReportedAt }}</q-card-section>
              </q-card>
            </div>
          </q-scroll-area>
        </q-card>
        <div class="row">
          <div class="col-7">
            <div class="row justify-center">
              <div class="col-12">
                <q-card class="q-mr-sm">
                  <q-card-section class="text-center">
                    <q-btn-dropdown
                      no-caps
                      flat
                      :label="timespan.label"
                      v-model="timespanMenu"
                      style="margin-bottom:2.20px"
                    >
                      <q-list>
                        <q-item
                          clickable
                          v-close-popup
                          no-caps
                          @click="timespan.label = 'For the last day'; timespan.value = 86400; getOverview()"
                        >
                          <q-item-section>
                            <q-item-label>For the last day</q-item-label>
                          </q-item-section>
                        </q-item>
                        <q-item
                          clickable
                          v-close-popup
                          no-caps
                          @click="timespan.label = 'For the last week'; timespan.value = 604800; getOverview()"
                        >
                          <q-item-section>
                            <q-item-label>For the last week</q-item-label>
                          </q-item-section>
                        </q-item>
                        <q-item
                          clickable
                          v-close-popup
                          @click="timespan.label = 'For the last 30 days'; timespan.value = 2592000; getOverview()"
                        >
                          <q-item-section>
                            <q-item-label>For the last 30 days</q-item-label>
                          </q-item-section>
                        </q-item>
                        <q-item clickable>
                          <q-item-section v-ripple>
                            <q-item-label>Custom range</q-item-label>
                            <q-popup-proxy
                              @before-show="updateProxy"
                              transition-show="scale"
                              transition-hide="scale"
                            >
                              <q-date v-model="dateRange" :options="dateOptions" range>
                                <div class="row items-center justify-end q-gutter-sm">
                                  <q-btn label="Cancel" color="primary" flat v-close-popup />
                                  <q-btn
                                    label="OK"
                                    color="primary"
                                    flat
                                    @click="timespan.value = dateRange; timespanMenu = false; getOverview()"
                                    v-close-popup
                                  />
                                </div>
                              </q-date>
                            </q-popup-proxy>
                          </q-item-section>
                        </q-item>
                      </q-list>
                    </q-btn-dropdown>
                    <div>
                      <span class="text-h6">{{ totalClients }}</span>
                      <span class="text-weight-normal q-mx-sm">clients,</span>
                      <span class="text-h6">{{ totalUsage }}</span>
                    </div>
                  </q-card-section>
                </q-card>
              </div>
            </div>

            <q-card class="q-mr-sm q-mt-sm">
              <q-table
                :pagination="pagination"
                row-key="networkId"
                :rows="rows"
                :columns="columns"
                :loading="tableLoading"
              >
                <template v-slot:top-left>
                  <q-btn
                    flat
                    dense
                    @click="timespan.label = 'For the last day'; timespan.value = 86400; getOverview()"
                    icon="refresh"
                    label="Overview"
                  />
                </template>
                <template v-slot:body="props">
                  <q-tr :props="props">
                    <q-td key="name" :props="props">{{ props.row.name }}</q-td>
                    <q-td key="productType" :props="props">{{ props.row.productType }}</q-td>
                    <q-td key="usageTotal" :props="props">{{ props.row.usage.total }}</q-td>
                    <q-td key="usagePercentage" :props="props">
                      {{ (props.row.usage.percentage).toFixed(0) }}%
                      <q-linear-progress :value="props.row.usage.progress" />
                    </q-td>
                    <q-td key="clients" :props="props">{{ props.row.clients }}</q-td>
                  </q-tr>
                </template>
              </q-table>
            </q-card>
          </div>
          <div class="col-5">
            <TopClientsTable
              :organizationID="organizationID"
              :organizationName="organizationName"
              @onNotifyError="onNotifyError"
            />
          </div>
        </div>
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
import RemoveOrgAssociation from "@/components/integrations/meraki/modals/RemoveOrgAssociation";
import TopClientsTable from "@/components/integrations/meraki/organization/TopClientsTable";
import NetworkTrafficAnalyticsTable from "@/components/integrations/meraki/traffic/NetworkTrafficAnalyticsTable";
import NetworkClientsTrafficTable from "@/components/integrations/meraki/traffic/NetworkClientsTrafficTable";
import NetworkEventsTable from "@/components/integrations/meraki/events/NetworkEventsTable";
// composable imports
import { ref, onBeforeMount } from "vue";
import { useQuasar, date } from "quasar";
import { notifySuccess, notifyError } from "@/utils/notify";

const columns = [
  {
    name: "name",
    required: true,
    label: "Name",
    align: "left",
    field: (row) => row.name,
    format: (val) => `${val}`,
    sortable: true,
  },

  {
    name: "productType",
    align: "left",
    label: "Type",
    field: "productType",
    sortable: true,
  },
  {
    name: "usageTotal",
    align: "left",
    label: "Usage",
    field: "usageTotal",
    sortable: false,
  },
  {
    name: "usagePercentage",
    align: "left",
    label: "% Used",
    field: "usagePercentage",
    sortable: false,
  },
  {
    name: "clients",
    align: "left",
    label: "Clients",
    field: "clients",
    sortable: true,
  },
];

export default {
  name: "ClientMeraki",
  props: ['node', 'integrations'],
  components: {
    AssociateOrg,
    RemoveOrgAssociation,
    TopClientsTable,
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
    const rows = ref([])
    const uplinks = ref("")
    const timespan = ref({ label: "For the last day", value: 86400 })
    const timespanMenu = ref(false)
    const totalClients = ref(null)
    const totalUsage = ref(null)
    const dateOptions = ref([])
    const dateRange = ref("")
    const updateProxy = ref("")
    const tableLoading = ref(false)

    function formatUsage(usage) {
      if (usage < 1000) {
        let totalMB = usage.toFixed(2)
        return String(totalMB) + " MB"

      } else if (usage > 1000 && usage <= 1000000) {
        let totalGB = (usage / 1000).toFixed(2)
        return String(totalGB) + " GB"

      } else if (usage > 1000000 && usage <= 1000000000) {
        let totalTB = (usage / 1000000).toFixed(2)
        return String(totalTB) + " TB"
      }
    }

    function checkAssociation() {
      timespan.value = { label: "For the last day", value: 86400 }
      let obj = null
      for (let i = 0; i < props.integrations.length; i++) {
        obj = props.integrations[i].configuration.backend.associations.clients.find(o => o.client_id === props.node.id);
        if (obj) {
          break;
        }
      }

      if (obj) {
        getOrganization(obj)
      } else {
        $q.dialog({
          component: AssociateOrg,
        }).onOk(val => {
          let data = {
            client_id: props.node.id,
            meraki_organization_id: parseInt(val['meraki_organization_id']),
            meraki_organization_label: val['meraki_organization_label']
          }
          axios
            .put(`/integrations/` + props.integrations[0].id + `/associate_client/`, data)
            .then(r => {
              if (r.data.errors) {
                notifyError(r.data.errors[0])

              } else {
                notifySuccess(val['meraki_organization_label'] + ' is now associated with ' + props.node.name)
                getOrganization(val)
              }
            })
            .catch(e => {
              console.log(e)
            });
        })
      }
    }

    function getOrganization(obj) {
      $q.loading.show({ message: 'Getting ' + props.node.name + ' networks...' })
      axios
        .get(`/meraki/organizations/` + obj.meraki_organization_id)
        .then(r => {
          if (r.data.errors) {
            notifyError(r.data.errors[0])

          } else {
            organizationID.value = r.data.id
            organizationName.value = r.data.name
            organization.value = r.data;
            getNetworks()
          }

        })
        .catch(e => {

        });
    }

    function getNetworks() {
      axios
        .get(`/meraki/` + organizationID.value + `/networks/`)
        .then(r => {
          if (r.data.errors) {
            notifyError(r.data.errors[0])

          } else {
            networks.value = r.data;
            getUplinks()
          }
        })
        .catch(e => {

        });
    }

    function getUplinks() {
      $q.loading.show({ message: 'Producing a summary for ' + props.node.name + '...' })

      axios
        .get(`/meraki/` + organizationID.value + `/networks/uplinks/`)
        .then(r => {
          if (r.data.errors) {
            notifyError(r.data.errors[0])

          } else {
            uplinks.value = r.data
            tab.value = 'summary'
            getOverview()
          }
        })
        .catch(e => {

        });
    }

    function getOverview() {
      tableLoading.value = true
      for (let i = 0; i < 31; i++) {
        let newDate = date.subtractFromDate(new Date(), { days: i });
        let formattedDate = date.formatDate(newDate, "YYYY/MM/DD");
        dateOptions.value.push(formattedDate);
      }

      if (timespan.value.value.from && timespan.value.value.to) {
        const t0 = date.formatDate(timespan.value.value.from, "YYYY-MM-DDT00:00:00.000Z");
        const t1 = date.formatDate(timespan.value.value.to, "YYYY-MM-DDT23:59:00.000Z");
        timespan.value.value = "t0=" + t0 + "&t1=" + t1
        timespan.value.label = date.formatDate(t0, "MMM D, YYYY @ hh:mm A") + " - " + date.formatDate(t1, "MMM D, YYYY @ hh:mm A")



      } else if (typeof timespan.value.value !== 'object' && timespan.value.value !== 86400 && timespan.value.value !== 604800 && timespan.value.value !== 2592000) {
        const t0 = date.formatDate(timespan.value.value, "YYYY-MM-DDT00:00:00.000Z");
        const t1 = date.formatDate(timespan.value.value, "YYYY-MM-DDT23:59:00.000Z");
        timespan.value.value = "t0=" + t0 + "&t1=" + t1
        timespan.value.label = date.formatDate(t0, "MMM D, YYYY @ hh:mm A") + " - " + date.formatDate(t1, "MMM D, YYYY @ hh:mm A")
      }

      axios
        .get(`/meraki/` + organizationID.value + `/overview/` + timespan.value.value + `/`)
        .then(r => {
          if (r.data.errors) {
            notifyError(r.data.errors[0])

          } else {
            rows.value = []
            totalUsage.value = 0
            totalClients.value = 0
            for (let device of r.data) {
              let returnedUsage = formatUsage(device.usage.total)
              totalUsage.value += device.usage.total
              totalClients.value += device.clients.counts.total

              let deviceObj = {
                clients: device.clients.counts.total,
                mac: device.mac,
                model: device.model,
                name: device.name,
                networkId: device.network.id,
                networkName: device.network.name,
                productType: device.productType,
                serial: device.serial,
                usage: { total: returnedUsage, percentage: device.usage.percentage, progress: device.usage.percentage / 100 },
              }
              rows.value.push(deviceObj)
            }

            let returnedTotalUsage = formatUsage(totalUsage.value)
            totalUsage.value = returnedTotalUsage
            $q.loading.hide()
            tableLoading.value = false
          }
        })
        .catch(e => {
          // notifyError(e)
          console.log(e)
        });
    }

    function changeAssociation() {
      $q.dialog({
        component: AssociateOrg,
        componentProps: {
          integrations: props.integrations,
          organization: organization.value,
          client: props.node
        }
      }).onOk(() => {
        checkAssociation()
      })
    }

    function removeOrgAssociation() {
      $q.dialog({
        component: RemoveOrgAssociation,
        componentProps: {
          integration: props.integrations[0],
          organization: organization.value,
          client: props.node
        }
      })
    }

    function onNotifyError(error) {
      notifyError(error[0])
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

    onBeforeMount(() => {
      checkAssociation()
    })

    return {
      pagination: {
        sortBy: 'percentage',
        descending: true,
        page: 1,
        rowsPerPage: 10
      },
      rows,
      columns,
      uplinks,
      timespan,
      timespanMenu,
      totalClients,
      totalUsage,
      dateOptions,
      dateRange,
      updateProxy,
      tableLoading,
      tab,
      splitterModel: ref(17),
      organization,
      networks,
      organizationID,
      organizationName,
      networkName,
      networkId,
      onNotifyError,
      checkAssociation,
      getUplinks,
      getOverview,
      getNetworks,
      getNetworkApplicationTraffic,
      getNetworkClientTraffic,
      getNetworkEventsTable,
      changeAssociation,
      removeOrgAssociation,
    };
  },
};
</script>

<style lang="sass">
.menu-link
  color: black
  background: #eeeeee
</style>