<template>
  <div class="row justify-center">
    <div class="col-6">
      <q-card>
        <q-card-section class="text-center">
          <span class="text-weight-light">Total</span>
          <div>
            <span class="text-h6">{{ totalUsage }}</span>
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
                  @click="timespan.label = 'for the last 2 hours'; timespan.value = 7200; getTrafficAnalytics()"
                >
                  <q-item-section>
                    <q-item-label>for the last 2 hours</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item
                  clickable
                  v-close-popup
                  no-caps
                  @click="timespan.label = 'for the last day'; timespan.value = 86400; getTrafficAnalytics()"
                >
                  <q-item-section>
                    <q-item-label>for the last day</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item
                  clickable
                  v-close-popup
                  no-caps
                  @click="timespan.label = 'for the last week'; timespan.value = 604800; getTrafficAnalytics()"
                >
                  <q-item-section>
                    <q-item-label>for the last week</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item
                  clickable
                  v-close-popup
                  @click="timespan.label = 'for the last 30 days'; timespan.value = 2592000; getTrafficAnalytics()"
                >
                  <q-item-section>
                    <q-item-label>for the last 30 days</q-item-label>
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
                            @click="timespan.value = dateRange; timespanMenu = false; getTrafficAnalytics()"
                            v-close-popup
                          />
                        </div>
                      </q-date>
                    </q-popup-proxy>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-btn-dropdown>
          </div>
        </q-card-section>
      </q-card>
    </div>
  </div>
  <div class="row justify-center q-my-sm">
    <div class="col-3 q-pr-sm">
      <q-card>
        <q-card-section class="text-center">
          <span class="text-weight-light">Downloaded</span>
          <div class="text-h6">{{ totalRecv }}</div>
        </q-card-section>
      </q-card>
    </div>
    <div class="col-3">
      <q-card>
        <q-card-section class="text-center">
          <span class="text-weight-light">Uploaded</span>
          <div class="text-h6">{{ totalSent }}</div>
        </q-card-section>
      </q-card>
    </div>
  </div>
  <q-table
    :rows="rows"
    :columns="columns"
    row-key="id"
    :pagination="pagination"
    :loading="tableLoading"
    :filter="filter"
  >
    <template v-slot:top-left>
      <div>
        <q-btn
          flat
          dense
          @click="timespan.label = 'for the last 2 hours'; timespan.value = 7200; getClientTraffic()"
          icon="refresh"
          label="Client Traffic"
          class="q-mr-md"
        />
      </div>
    </template>
    <template v-slot:top-right>
      <div>
        <q-input outlined clearable dense debounce="300" v-model="filter" label="Search">
          <template v-slot:prepend>
            <q-icon name="search" />
          </template>
        </q-input>
      </div>
    </template>

    <template v-slot:body="props">
      <q-tr :props="props">
        <q-td key="status" :props="props">
          <q-icon v-if="props.row.status == 'Online'" name="brightness_1" color="positive" />
          <q-icon v-else name="brightness_1" color="negative" />
        </q-td>
        <q-td key="id" :props="props">
          <q-btn
            flat
            no-caps
            class="text-caption text-weight-bold q-px-none"
            @click="getDevicePolicy(props.row)"
          >{{ props.row.id }}</q-btn>
        </q-td>
        <q-td key="name" :props="props">
          <span class="text-caption">{{ props.row.name }}</span>
        </q-td>
        <q-td key="user" :props="props">
          <span class="text-caption">{{ props.row.user }}</span>
        </q-td>
        <q-td key="description" :props="props">
          <span class="text-caption">{{ props.row.description }}</span>
        </q-td>
        <q-td key="ip" :props="props">
          <span class="text-caption">{{ props.row.ip }}</span>
        </q-td>
        <q-td key="mac" :props="props">
          <span class="text-caption">{{ props.row.mac }}</span>
        </q-td>
        <q-td key="usageTotal" :props="props">
          <span class="text-caption">{{ props.row.usage.total }}</span>
        </q-td>
        <q-td key="firstSeen" :props="props">
          <span class="text-caption">{{ props.row.firstSeen }}</span>
        </q-td>
        <q-td key="lastSeen" :props="props">
          <span class="text-caption">{{ props.row.lastSeen }}</span>
        </q-td>
        <q-td key="os" :props="props">
          <span class="text-caption">{{ props.row.os }}</span>
        </q-td>
        <q-td key="vlan" :props="props">
          <span class="text-caption">{{ props.row.vlan }}</span>
        </q-td>
      </q-tr>
    </template>
  </q-table>
</template>

<script>
import axios from "axios";
import { ref, onMounted } from "vue";
import { useQuasar, date } from "quasar";
import Policy from "@/components/integrations/meraki/modals/Policy";

const columns = [
  {
    name: "status",
    label: "Status",
    align: "left",
    field: (row) => row.status,
    format: (val) => `${val}`,
    sortable: true,
  },
  {
    name: "id",
    align: "left",
    label: "ID",
    field: "id",
    sortable: true,
  },

  {
    name: "name",
    align: "left",
    label: "Name",
    field: "name",
    sortable: true,
  },
  {
    name: "user",
    align: "left",
    label: "User",
    field: "user",
    sortable: true,
  },
  {
    name: "description",
    align: "left",
    label: "Description",
    field: "description",
    sortable: true,
  },
  {
    name: "ip",
    label: "IPv4",
    field: "ip",
    align: "left",
    sortable: true,
  },
  {
    name: "usageTotal",
    label: "Usage",
    field: "usageTotal",
    align: "left",
    sortable: false,
  },
  {
    name: "firstSeen",
    label: "First Seen",
    field: "firstSeen",
    align: "left",
    sortable: true,
  },
  {
    name: "lastSeen",
    label: "Last Seen",
    field: "lastSeen",
    align: "left",
    sortable: true,
  },
  {
    name: "os",
    label: "OS",
    field: "os",
    align: "left",
    sortable: true,
  },
  {
    name: "vlan",
    label: "VLAN",
    field: "vlan",
    align: "left",
    sortable: true,
  }
];

export default {
  name: "NetworkClientsTrafficTable",
  props: ["organizationName", "networkID", "networkName"],

  setup(props) {
    const $q = useQuasar();

    const timespanMenu = ref(false)
    const timespan = ref({ label: "for the last 2 hours", value: 7200 })
    const rows = ref([])
    const totalUsage = ref(null)
    const totalRecv = ref(null)
    const totalSent = ref(null)
    const filter = ref("")
    const dateOptions = ref([])
    const dateRange = ref("")
    const updateProxy = ref("")
    const tableLoading = ref(false)

    function formatUsage(usage) {
      if (usage < 1000) {
        let totalKB = usage.toFixed(0)
        return String(totalKB) + " KB"

      } else if (usage > 1000 && usage < 1000000) {
        let totalMB = (usage / 1000).toFixed(2)
        return String(totalMB) + " MB"

      } else if (usage > 1000000 && usage < 1000000000) {
        let totalGB = (usage / 1000000).toFixed(2)
        return String(totalGB) + " GB"

      } else if (usage > 1000000000 && usage < 1000000000000) {
        let totalTB = (usage / 1000000000).toFixed(2)
        return String(totalTB) + " TB"

      }
    }

    function getClientTraffic() {
      tableLoading.value = true

      for (let i = 0; i < 31; i++) {
        let newDate = date.subtractFromDate(new Date(), { days: i });
        let formattedDate = date.formatDate(newDate, "YYYY/MM/DD");
        dateOptions.value.push(formattedDate);
      }

      if (typeof timespan.value.value === 'object') {
        const t0 = date.formatDate(timespan.value.value.from, "YYYY-MM-DDT00:00:00.000Z");
        const t1 = date.formatDate(timespan.value.value.to, "YYYY-MM-DDT23:59:00.000Z");
        timespan.value.value = "t0=" + t0 + "&t1=" + t1
        timespan.value.label = date.formatDate(t0, "MMM D, YYYY @ hh:mm A") + " - " + date.formatDate(t1, "MMM D, YYYY @ hh:mm A")

      } else if (timespan.value.value !== 7200 && timespan.value.value !== 86400 && timespan.value.value !== 604800 && timespan.value.value !== 2592000) {
        const t0 = date.formatDate(timespan.value.value, "YYYY-MM-DDT00:00:00.000Z");
        const t1 = date.formatDate(timespan.value.value, "YYYY-MM-DDT23:59:00.000Z");
        timespan.value.value = "t0=" + t0 + "&t1=" + t1
        timespan.value.label = date.formatDate(t0, "MMM D, YYYY @ hh:mm A") + " - " + date.formatDate(t1, "MMM D, YYYY @ hh:mm A")
      }

      axios
        .get(`/meraki/` + props.networkID + `/clients/traffic/` + timespan.value.value + `/`)
        .then(r => {
          rows.value = []
          totalUsage.value = 0
          totalRecv.value = 0
          totalSent.value = 0

          for (let client of r.data) {
            let returnedUsage = formatUsage(client.usage.total)
            totalUsage.value += client.usage.total
            totalRecv.value += client.usage.recv
            totalSent.value += client.usage.sent

            let clientObj = {
              status: client.status,
              id: client.id,
              name: client.name,
              user: client.user,
              description: client.description,
              ip: client.ip,
              mac: client.mac,
              usage: { total: returnedUsage, recv: client.usage.recv, sent: client.usage.sent },
              recentDeviceMac: client.recentDeviceMac,
              recentDeviceName: client.recentDeviceName,
              firstSeen: date.formatDate(client.firstSeen, "MMM DD, YYYY @ h:mm A"),
              lastSeen: date.formatDate(client.lastSeen, "MMM DD, YYYY @ h:mm A"),
              os: client.os,
              vlan: client.vlan
            }
            rows.value.push(clientObj)
          }
          let returnedTotalUsage = formatUsage(totalUsage.value)
          let returnedTotalRecv = formatUsage(totalRecv.value)
          let returnedTotalSent = formatUsage(totalSent.value)

          totalUsage.value = returnedTotalUsage
          totalRecv.value = returnedTotalRecv
          totalSent.value = returnedTotalSent
          tableLoading.value = false
        })
        .catch(e => {

        });
    }

    function getDevicePolicy(client) {
      $q.dialog({
        component: Policy,
        componentProps: {
          networkId: props.networkID,
          client: client
        }
      })
    }

    onMounted(() => {
      getClientTraffic();
    })

    return {
      pagination: {
        sortBy: 'lastSeen',
        descending: true,
        page: 1,
        rowsPerPage: 10
      },
      timespanMenu,
      timespan,
      columns,
      rows,
      totalUsage,
      totalRecv,
      totalSent,
      filter,
      dateOptions,
      dateRange,
      updateProxy,
      tableLoading,
      getClientTraffic,
      getDevicePolicy
    };
  }
}
</script>