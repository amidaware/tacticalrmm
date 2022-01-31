<template>
  <div class="row justify-center">
    <div class="col-6">
      <q-card>
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
                @click="timespan.label = 'For the last 2 hours'; timespan.value = 7200; getTrafficAnalytics()"
              >
                <q-item-section>
                  <q-item-label>For the last 2 hours</q-item-label>
                </q-item-section>
              </q-item>
              <q-item
                clickable
                v-close-popup
                no-caps
                @click="timespan.label = 'For the last day'; timespan.value = 86400; getTrafficAnalytics()"
              >
                <q-item-section>
                  <q-item-label>For the last day</q-item-label>
                </q-item-section>
              </q-item>
              <q-item
                clickable
                v-close-popup
                no-caps
                @click="timespan.label = 'For the last week'; timespan.value = 604800; getTrafficAnalytics()"
              >
                <q-item-section>
                  <q-item-label>For the last week</q-item-label>
                </q-item-section>
              </q-item>
              <q-item
                clickable
                v-close-popup
                @click="timespan.label = 'For the last 30 days'; timespan.value = 2592000; getTrafficAnalytics()"
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
          <div>
            <span class="text-h6">{{ totalUsage }}</span>
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
    :visible-columns="visibleColumns"
  >
    <template v-slot:top-left>
      <div>
        <q-btn
          flat
          dense
          @click="timespan.label = 'For the last 2 hours'; timespan.value = 7200; getTrafficAnalytics()"
          icon="refresh"
          label="Traffic analytics"
          class="q-mr-md"
        />
      </div>
    </template>
    <template v-slot:top-right>
      <q-input outlined clearable dense debounce="300" v-model="filter" label="Search">
        <template v-slot:prepend>
          <q-icon name="search" />
        </template>
      </q-input>
    </template>
    <template v-slot:body="props">
      <q-tr :props="props">
        <q-td key="application" :props="props">
          {{ props.row.application }}
        </q-td>
        <q-td key="destination" :props="props">
          <q-btn
            type="a"
            no-caps
            class="q-pa-none text-weight-bold"
            flat
            :href="'https://viewdns.info/whois/?domain=' + props.row.destination"
            target="_blank"
            :label="props.row.destination"
          />
        </q-td>
        <q-td key="protocol" :props="props">
          {{ props.row.protocol }}
        </q-td>
        <q-td key="port" :props="props">
          {{ props.row.port }}
        </q-td>
        <q-td key="usageTotal" :props="props">
          {{ props.row.usage.total }}
        </q-td>
        <q-td key="totalUsage" :props="props">
          {{ props.row.usage.total }}
        </q-td>
        <q-td key="flows" :props="props">
          {{ props.row.flows }}
        </q-td>
        <q-td key="activeTime" :props="props">
          {{ props.row.activeTime }}
        </q-td>
        <q-td key="numClients" :props="props">
          {{ props.row.numClients }}
        </q-td>
      </q-tr>
    </template>
  </q-table>
</template>

<script>
import axios from "axios";
import { ref, onMounted } from "vue";
import { date } from "quasar";

const columns = [
  {
    name: "application",
    required: true,
    label: "Application",
    align: "left",
    field: (row) => row.application,
    format: (val) => `${val}`,
    sortable: true,
  },
  {
    name: "destination",
    align: "left",
    label: "Destination",
    field: "destination",
    sortable: true,
  },
  {
    name: "protocol",
    label: "Protocol",
    field: "protocol",
    align: "left",
    sortable: true,
  },
  { name: "port", label: "Port", field: "port", align: "left", sortable: true },
  {
    name: "usageTotal",
    label: "Usage",
    field: "usageTotal",
    align: "left",
    sortable: false,
  },
  {
    name: "totalUsage",
    label: "Total Usage",
    field: "totalUsage",
    align: "left",
    field: (row) => row.totalUsage,
    format: (val) => `${val}`,
    sortable: true
  },
  {
    name: "flows",
    label: "Flows",
    field: "flows",
    align: "left",
    sortable: true,
  },
  {
    name: "activeTime",
    label: "Active Time",
    field: "activeTime",
    align: "left",
    sortable: false,
  },
  {
    name: "numClients",
    label: "# of Clients",
    field: "numClients",
    align: "left",
    sortable: true,
  },
];

export default {
  name: "NetworkApplicationTrafficTable",
  props: ["organizationID", "organizationName", "networkID", "networkName"],
  setup(props) {
    const timespanMenu = ref(false)
    const timespan = ref({ label: "For the last 2 hours", value: 7200 })
    const rows = ref([])
    const totalActiveTime = ref(null)
    const totalUsage = ref(null)
    const totalRecv = ref(null)
    const totalSent = ref(null)
    const filter = ref("")
    const dateOptions = ref([])
    const dateRange = ref("")
    const updateProxy = ref("")
    const tableLoading = ref(false)

    function formatUsage(usage) {
      if (usage < 1024) {
        let totalKB = usage.toFixed(0)
        return String(totalKB) + " KB"

      } else if (usage / 1024 < 1024) {
        let totalMB = (usage / 1024).toFixed(2)
        return String(totalMB) + " MB"

      } else if (usage / 1024 / 1024 < 1024) {
        let totalGB = (usage / 1024 / 1024).toFixed(2)
        return String(totalGB) + " GB"

      } else if (usage / 1024 / 1024 / 1024 < 1024) {
        let totalTB = (usage / 1024 / 1024 / 1024).toFixed(2)
        return String(totalTB) + " TB"

      }
    }

    function formatTime(time) {
      if (time / 60 / 60 > 24) {
        let totalDays = (time / 60 / 60 / 24).toFixed(1)
        return String(totalDays) + " days"

      } else if (time / 60 > 60) {
        let totalHours = (time / 60 / 60).toFixed(1)
        return String(totalHours) + " hours"

      } else if (time / 60 < 60) {
        let totalMinutes = (time / 60).toFixed(0)
        return String(totalMinutes) + " minutes"

      }
    }

    function getTrafficAnalytics() {
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
        .get(`/meraki/` + props.networkID + `/applications/traffic/` + timespan.value.value + `/`)
        .then(r => {
          rows.value = []
          totalUsage.value = 0
          totalRecv.value = 0
          totalSent.value = 0

          for (let application of r.data) {
            let returnedRecvSent = application.recv + application.sent
            let returnedUsage = formatUsage(returnedRecvSent)
            let returnedActiveTime = formatTime(application.activeTime)

            totalUsage.value += returnedRecvSent
            totalRecv.value += application.recv
            totalSent.value += application.sent

            let appObj = {
              application: application.application,
              destination: application.destination,
              protocol: application.protocol,
              port: application.port,
              usage: { total: returnedUsage, recv: application.recv, sent: application.sent },
              totalUsage: application.recv + application.sent,
              flows: application.flows,
              activeTime: returnedActiveTime,
              numClients: application.numClients,
            }
            rows.value.push(appObj)
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

    onMounted(() => {
      getTrafficAnalytics();
    })


    return {
      pagination: {
        sortBy: 'totalUsage',
        descending: true,
        page: 1,
        rowsPerPage: 10
      },
      visibleColumns: ref(['application', 'destination', 'protocol', 'port', 'usageTotal', 'flows', 'activeTime', 'numClients']),
      timespanMenu,
      timespan,
      columns,
      rows,
      totalActiveTime,
      totalUsage,
      totalRecv,
      totalSent,
      filter,
      dateOptions,
      dateRange,
      updateProxy,
      tableLoading,
      getTrafficAnalytics,
    };
  }
}
</script>