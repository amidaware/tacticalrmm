<template>
  <q-card flat bordered class="q-mb-sm">
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
            @click="timespan.label = 'For the last day'; timespan.value = 86400; getTopClients()"
          >
            <q-item-section>
              <q-item-label>For the last day</q-item-label>
            </q-item-section>
          </q-item>
          <q-item
            clickable
            v-close-popup
            no-caps
            @click="timespan.label = 'For the last week'; timespan.value = 604800; getTopClients()"
          >
            <q-item-section>
              <q-item-label>For the last week</q-item-label>
            </q-item-section>
          </q-item>
          <q-item
            clickable
            v-close-popup
            @click="timespan.label = 'For the last 30 days'; timespan.value = 2592000; getTopClients()"
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
                      @click="timespan.value = dateRange; timespanMenu = false; getTopClients()"
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
        <span class="text-weight-normal q-ml-sm">
          (
          <q-icon name="arrow_downward" />
          {{ totalDownstream }},
          <q-icon name="arrow_upward" />
          {{ totalUpstream }})
        </span>
      </div>
    </q-card-section>
  </q-card>
  <q-card flat bordered>
    <q-table
      class="q-mt-sm"
      :rows="rows"
      :columns="columns"
      row-key="name"
      :pagination="pagination"
      :loading="tableLoading"
    >
      <template v-slot:top-left>
        <q-btn
          flat
          dense
          @click="timespan.label = 'for the last day'; timespan.value = 86400; getTopClients()"
          icon="refresh"
          label="Top 10 Clients"
        />
      </template>
      <template v-slot:body="props">
        <q-tr :props="props">
          <q-td key="name" :props="props">
            <span class="text-caption">{{ props.row.name }}</span>
          </q-td>
          <q-td key="networkName" :props="props">
            <span class="text-caption">{{ props.row.networkName }}</span>
          </q-td>

          <q-td key="usageTotal" :props="props">
            <span class="text-caption">{{ props.row.usage.total }}</span>
          </q-td>
          <q-td key="usagePercentage" :props="props">
            <span class="text-caption">{{ props.row.usage.percentage.toFixed(0) }}%</span>
            <q-linear-progress :value="props.row.usage.progress" color="positive"></q-linear-progress>
          </q-td>
        </q-tr>
      </template>
    </q-table>
  </q-card>
</template>

<script>
import axios from "axios";
import { ref, onMounted } from "vue";
import { date } from "quasar";

const columns = [
  // {
  //   name: "id",
  //   required: true,
  //   label: "ID",
  //   align: "left",
  //   field: (row) => row.id,
  //   format: (val) => `${val}`,
  //   sortable: true,
  // },
  {
    name: "name",
    align: "left",
    label: "Name",
    field: "name",
    field: (row) => row.name,
    format: (val) => `${val}`,
    sortable: true,
  },
  {
    name: "networkName",
    align: "left",
    label: "Network",
    field: "networkName",
    sortable: true,
  },
  // {
  //   name: "mac",
  //   label: "MAC",
  //   field: "mac",
  //   align: "left",
  //   sortable: true,
  // },
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
];

function wrapCsvValue(val, formatFn) {
  let formatted = formatFn !== void 0 ? formatFn(val) : val;
  formatted = formatted === void 0 || formatted === null ? "" : String(formatted);
  formatted = formatted.split('"').join('""');

  return `"${formatted}"`;
}
export default {
  name: "TopClientsTable",
  props: ["organizationID", "organizationName"],
  setup(props) {
    const tableLoading = ref(false)
    const rows = ref([])
    const uplinks = ref([])
    const timespanMenu = ref(false)
    const timespan = ref({ label: "For the last day", value: 86400 })
    const dateOptions = ref([])
    const dateRange = ref("")
    const updateProxy = ref("")
    const totalUsage = ref(null)
    const totalDownstream = ref(null)
    const totalUpstream = ref(null)

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

    function getTopClients() {
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

      } else if (timespan.value.value !== 86400 && timespan.value.value !== 604800 && timespan.value.value !== 2592000) {
        const t0 = date.formatDate(timespan.value.value, "YYYY-MM-DDT00:00:00.000Z");
        const t1 = date.formatDate(timespan.value.value, "YYYY-MM-DDT23:59:00.000Z");
        timespan.value.value = "t0=" + t0 + "&t1=" + t1
        timespan.value.label = date.formatDate(t0, "MMM D, YYYY @ hh:mm A") + " - " + date.formatDate(t1, "MMM D, YYYY @ hh:mm A")
      }

      axios
        .get(`meraki/` + props.organizationID + `/top_clients/` + timespan.value.value + `/`)
        .then(r => {
          rows.value = []
          totalUsage.value = 0
          totalDownstream.value = 0
          totalUpstream.value = 0

          for (let client of r.data) {
            let returnedUsage = formatUsage(client.usage.total)
            totalUsage.value += client.usage.total
            totalDownstream.value += client.usage.downstream
            totalUpstream.value += client.usage.upstream

            let clientObj = {
              id: client.id,
              mac: client.mac,
              name: client.name,
              networkId: client.network.id,
              networkName: client.network.name,
              usage: { total: returnedUsage, downstream: client.usage.downstream, upstream: client.usage.upstream, percentage: client.usage.percentage, progress: client.usage.percentage / 100 },
            }
            rows.value.push(clientObj)
          }

          let returnedTotalUsage = formatUsage(totalUsage.value)
          let returnedTotalDownstream = formatUsage(totalDownstream.value)
          let returnedTotalUpstream = formatUsage(totalUpstream.value)

          totalUsage.value = returnedTotalUsage
          totalDownstream.value = returnedTotalDownstream
          totalUpstream.value = returnedTotalUpstream
          tableLoading.value = false
        })
        .catch(e => {

        });

    }

    function exportTable() {
      const content = [columns.value.map((col) => wrapCsvValue(col.label))]
        .concat(
          rows.value.map((row) =>
            columns.value
              .map((col) =>
                wrapCsvValue(
                  typeof col.field === "function"
                    ? col.field(row)
                    : row[col.field === void 0 ? col.name : col.field],
                  col.format
                )
              )
              .join(",")
          )
        )
        .join("\r\n");

      const status = exportFile("table-export.csv", content, "text/csv");

      if (status !== true) {
        $q.notify({
          message: "Browser denied file download...",
          color: "negative",
          icon: "warning",
        });
      }
    }

    onMounted(() => {
      getTopClients();
    })

    return {
      pagination: {
        sortBy: 'percentage',
        descending: true,
        page: 1,
        rowsPerPage: 10
      },
      tableLoading,
      rows,
      columns,
      uplinks,
      timespanMenu,
      timespan,
      dateOptions,
      dateRange,
      updateProxy,
      totalUsage,
      totalDownstream,
      totalUpstream,
      getTopClients,
      exportTable,
    };
  }
}
</script>