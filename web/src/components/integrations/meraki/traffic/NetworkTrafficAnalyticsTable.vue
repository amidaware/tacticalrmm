<template>
  <q-table
    :rows="rows"
    :columns="columns"
    row-key="id"
    :pagination="pagination"
    :loading="tableLoading"
    :filter="filter"
  >
    <template v-slot:top-left>
      <q-btn
        flat
        dense
        @click="timespan.label = 'for the last 2 hours'; timespan.value = 7200; getTrafficAnalytics()"
        icon="refresh"
        class="q-mb-sm q-mr-md"
      />
      <span class="text-h6">{{ totalUsage }}</span>
      <span class="q-pl-sm">transferred</span>
      <span>
        (
        <q-icon name="arrow_downward" />
        {{ totalRecv }},
        <q-icon name="arrow_upward" />
        {{ totalSent }})
      </span>
      <q-btn-dropdown
        no-caps
        flat
        :label="timespan.label"
        v-model="timespanMenu"
        class="q-mb-xs q-px-sm"
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
          <span class="text-caption">{{ props.row.application }}</span>
        </q-td>
        <q-td key="destination" :props="props">
          <q-btn
            type="a"
            no-caps
            class="q-pa-none text-caption text-weight-bold"
            flat
            :href="'https://viewdns.info/whois/?domain=' + props.row.destination"
            target="_blank"
            :label="props.row.destination"
          />
        </q-td>
        <q-td key="protocol" :props="props">
          <span class="text-caption">{{ props.row.protocol }}</span>
        </q-td>
        <q-td key="port" :props="props">
          <span class="text-caption">{{ props.row.port }}</span>
        </q-td>
        <q-td key="usageTotal" :props="props">
          <span class="text-caption">{{ props.row.usage.total }}</span>
        </q-td>
        <q-td key="flows" :props="props">
          <span class="text-caption">{{ props.row.flows }}</span>
        </q-td>
        <!-- <q-td key="recv" :props="props">
          <span class="text-caption">{{ props.row.recv }}</span>
        </q-td>
        <q-td key="sent" :props="props">
          <span class="text-caption">{{ props.row.sent }}</span>
        </q-td>-->
        <q-td key="activeTime" :props="props">
          <span class="text-caption">{{ props.row.activeTime }}</span>
        </q-td>
        <q-td key="numClients" :props="props">
          <span class="text-caption">{{ props.row.numClients }}</span>
        </q-td>
      </q-tr>
    </template>
  </q-table>
</template>

<script>
import axios from "axios";
import { ref, onMounted } from "vue";
import { useQuasar, date } from "quasar";

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
    const timespan = ref({ label: "for the last 2 hours", value: 7200 })
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
        let t0 = date.formatDate(timespan.value.value.from, "YYYY-MM-DDT00:00:00.000Z");
        let t1 = date.formatDate(timespan.value.value.to, "YYYY-MM-DDT00:00:00.000Z");
        timespan.value.value = "t0=" + t0 + "&t1=" + t1
        timespan.value.label = date.formatDate(t0, "MMM D, YYYY @ hh:mm A") + " - " + date.formatDate(t1, "MMM D, YYYY @ hh:mm A")

      } else if (timespan.value.value !== 7200 && timespan.value.value !== 86400 && timespan.value.value !== 604800 && timespan.value.value !== 2592000) {
        let t0 = date.formatDate(timespan.value.value, "YYYY-MM-DDT00:00:00.000Z");
        let t1 = date.formatDate(timespan.value.value, "YYYY-MM-DDT23:59:00.000Z");
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
            let test = application.recv + application.sent
            let returnedUsage = formatUsage(test)
            let returnedActiveTime = formatTime(application.activeTime)

            totalUsage.value += test
            totalRecv.value += application.recv
            totalSent.value += application.sent

            let appObj = {
              application: application.application,
              destination: application.destination,
              protocol: application.protocol,
              port: application.port,
              usage: { total: returnedUsage, recv: application.recv, sent: application.sent },
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
        sortBy: 'application',
        descending: false,
        page: 1,
        rowsPerPage: 10
      },
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