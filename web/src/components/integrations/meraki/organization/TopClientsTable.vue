<template>
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> allow Meraki integration dashboard at client level as well as agent
  <div class="q-pb-md q-pl-md q-gutter-sm">
    <q-breadcrumbs>
      <q-breadcrumbs-el icon="home" class="text-black" />
      <q-breadcrumbs-el class="text-black" :label="organizationName" />
      <q-breadcrumbs-el class="text-black" label="Top 10 clients" />
    </q-breadcrumbs>
  </div>
<<<<<<< HEAD
=======
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
>>>>>>> allow Meraki integration dashboard at client level as well as agent
  <q-table class="q-pt-md q-mb-xl" :rows="rows" :columns="columns" row-key="occurredAt" v-model:pagination="pagination"
    :loading="isLoading" :filter="filter" wrap-cells>
    <template v-slot:loading v-model="isLoading">
      <q-inner-loading showing color="primary" />
    </template>
    <template v-slot:top-left>
      <q-btn flat dense @click="getTopClients(timespan.value)" icon="refresh" />
      <q-btn-dropdown no-caps flat :label="timespan.label">
        <q-list>
          <q-item clickable v-close-popup no-caps @click="getTopClients(86400)">
            <q-item-section>
              <q-item-label>Over the past day</q-item-label>
            </q-item-section>
          </q-item>
          <q-item clickable v-close-popup no-caps @click="getTopClients(604800)">
            <q-item-section>
              <q-item-label> Over the past week </q-item-label>
            </q-item-section>
          </q-item>
          <q-item clickable v-close-popup @click="getTopClients(2592000)">
            <q-item-section>
              <q-item-label>Over the past 30 days</q-item-label>
            </q-item-section>
          </q-item>
          <q-item clickable>
            <q-item-section v-ripple>
              <q-item-label>Custom range</q-item-label>
              <q-popup-proxy @before-show="updateProxy" transition-show="scale" transition-hide="scale">
                <q-date v-model="dateRange" :options="dateOptions" range>
                  <div class="row items-center justify-end q-gutter-sm">
                    <q-btn label="Cancel" color="primary" flat v-close-popup />
                    <q-btn label="OK" color="primary" flat @click="getTopClients(dateRange)" v-close-popup />
                  </div>
                </q-date>
              </q-popup-proxy>
            </q-item-section>
          </q-item>
        </q-list>
      </q-btn-dropdown>
      <span class="text-h6 q-mr-sm">{{ totalTraffic }}</span>
      <span class="q-mr-sm text-weight-light">(
        <q-icon name="arrow_downward" />{{ totalTrafficRecv }},
        <q-icon name="arrow_upward" />{{ totalTrafficSent }}) transferred
      </span>
    </template>
    <template v-slot:top-right="props">
      <q-btn flat dense color="primary" icon="archive" no-caps class="q-ml-md" @click="exportTable" />
    </template>
    <template v-slot:body="props">
      <q-tr :props="props">
        <q-td key="number" :props="props">
          <span class="text-caption">{{ props.row.number }}</span>
        </q-td>
        <q-td key="name" :props="props">
          <span class="text-caption">{{ props.row.name }}</span>
        </q-td>
        <q-td key="network" :props="props">
          <span class="text-caption">{{ props.row.network }}</span>
        </q-td>
        <q-td key="mac" :props="props">
          <span class="text-caption">{{ props.row.mac }}</span>
        </q-td>
        <q-td key="usage" :props="props">
          <span class="text-caption">{{ props.row.usage }}</span>
        </q-td>
        <q-td key="percentage" :props="props">
          <span class="text-caption">{{ props.row.percentage.percent }}%</span>
          <q-linear-progress :value="props.row.percentage.progress" color="positive">
          </q-linear-progress>
        </q-td>
      </q-tr>
    </template>
  </q-table>
</template>

<script>
  import { ref } from "vue";
  import axios from "axios";
  import { date } from "quasar";
  import { exportFile, useQuasar } from "quasar";

  const columns = [
    {
      name: "number",
      align: "left",
      label: "#",
      field: "number",
      sortable: false,
    },
    {
      name: "name",
      required: true,
      label: "Name",
      align: "left",
      field: (row) => row.name,
      format: (val) => `${val}`,
      sortable: false,
    },
    {
      name: "network",
      align: "left",
      label: "Network",
      field: "network",
      sortable: false,
    },
    {
      name: "mac",
      align: "left",
      label: "MAC",
      field: "mac",
      sortable: false,
    },
    {
      name: "usage",
      label: "Usage",
      field: "usage",
      align: "left",
      sortable: false,
    },

    {
      name: "percentage",
      label: "% Used",
      field: "percentage",
      align: "left",
      sortable: false,
    },
  ];
  function wrapCsvValue(val, formatFn) {
    let formatted = formatFn !== void 0 ? formatFn(val) : val;

    formatted = formatted === void 0 || formatted === null ? "" : String(formatted);

    formatted = formatted.split('"').join('""');
    /**
     * Excel accepts \n and \r in strings, but some other CSV parsers do not
     * Uncomment the next two lines to escape new lines
     */
    // .split('\n').join('\\n')
    // .split('\r').join('\\r')

    return `"${formatted}"`;
  }
  export default {
    name: "TopClientsTable",
    props: ["tabPanel", "organizationID", "organizationName"],
    data() {
      return {
        pagination: {
          rowsPerPage: 10,
          sortBy: "percentage",
          descending: true,
        },
        isLoading: ref(false),
        rows: ref([]),
        columns,
        filter: ref(""),
        uplinks: ref([]),
        timespan: ref({ label: "Over the past day", value: 86400 }),
        totalClients: ref(0),
        totalDevicesUsage: ref(0),
        dateOptions: ref([]),
        dateRange: ref(""),
        updateProxy: ref(""),
        totalTraffic: 0,
        totalTrafficRecv: 0,
        totalTrafficSent: 0,
      };
    },
    methods: {
      getTopClients(time) {
        this.isLoading = true;
        let url = null;

        if (time === 86400) {
          this.timespan.label = "Over the past day";
          this.timespan.value = 86400;
        } else if (time === 604800) {
          this.timespan.label = "Over the past week";
          this.timespan.value = 604800;
        } else if (time === 2592000) {
          this.timespan.label = "Over the past 30 days";
          this.timespan.value = 2592000;
        }

        if (typeof time === "object" && typeof time !== null) {
          const formattedFrom = date.formatDate(time.from, "YYYY-MM-DDT00:00:00.000Z");
          const formattedTo = date.formatDate(time.to, "YYYY-MM-DDT00:00:00.000Z");
          const from = date.formatDate(time.from, "MMM DD, YYYY HH:MM aa");
          const to = date.formatDate(time.to, "MMM DD, YYYY HH:MM aa");
          this.timespan.label = from + " - " + to;
          url = "t0=" + formattedFrom + "&t1=" + formattedTo;
        } else if (typeof time === "number" && time !== null) {
          url = time;
        } else {
          url = 86400;
        }

        axios
          .get(`meraki/` + this.organizationID + `/top_clients/` + url + `/`)
          .then(r => {
            this.rows = [];
            this.totalTrafficObj = 0;
            this.totalTrafficRecvObj = 0;
            this.totalTrafficSentObj = 0;
            this.totalTraffic = 0;
            this.totalTrafficRecv = 0;
            this.totalTrafficSent = 0;
            let number = 1;
            for (let client of r.data) {
              let clientObj = {
                number: number++,
                name: client.name,
                network: client.network.name,
                mac: client.mac,
                usage:
                  client.usage.total > 1024
                    ? (client.usage.total / 1024).toFixed(2) + " GB"
                    : client.usage.total.toFixed(2) + " MB",
                percentage: {
                  progress: client.usage.percentage / 60,
                  percent: client.usage.percentage.toFixed(1),
                },
              };
              this.totalTrafficObj += client.usage.total;
              this.totalTrafficRecvObj += client.usage.downstream;
              this.totalTrafficSentObj += client.usage.upstream;
              this.rows.push(clientObj);
            }
            for (let i = 0; i < 30; i++) {
              let newDate = date.subtractFromDate(new Date(), { days: i });
              let formattedDate = date.formatDate(newDate, "YYYY/MM/DD");
              this.dateOptions.push(formattedDate);
            }
            this.totalTrafficObj > 1048576
              ? (this.totalTraffic = (this.totalTrafficObj / 1048576).toFixed(2) + " TB")
              : this.totalTrafficObj > 1024 && this.totalTrafficObj < 1048576
                ? (this.totalTraffic = (this.totalTrafficObj / 1024).toFixed(2) + " GB")
                : this.totalTrafficObj < 1024
                  ? (this.totalTraffic = (this.totalTrafficObj / 1024).toFixed(1) + " MB")
                  : "";

            this.totalTrafficRecvObj > 1048576
              ? (this.totalTrafficRecv =
                (this.totalTrafficRecvObj / 1048576).toFixed(2) + " TB")
              : this.totalTrafficRecvObj > 1024 && this.totalTrafficRecvObj < 1048576
                ? (this.totalTrafficRecv =
                  (this.totalTrafficRecvObj / 1024).toFixed(2) + " GB")
                : this.totalTrafficRecvObj < 1024
                  ? (this.totalTrafficRecv =
                    (this.totalTrafficRecvObj / 1024).toFixed(1) + " MB")
                  : "";

            this.totalTrafficSentObj > 1048576
              ? (this.totalTrafficSent =
                (this.totalTrafficSentObj / 1048576).toFixed(2) + " TB")
              : this.totalTrafficSentObj > 1024 && this.totalTrafficSentObj < 1048576
                ? (this.totalTrafficSent =
                  (this.totalTrafficSentObj / 1024).toFixed(2) + " GB")
                : this.totalTrafficSentObj < 1024
                  ? (this.totalTrafficSent =
                    (this.totalTrafficSentObj / 1024).toFixed(1) + " MB")
                  : "";
            this.isLoading = false;
          })
          .catch(e => {

          });

      },
      exportTable() {
        // naive encoding to csv format
        const content = [this.columns.map((col) => wrapCsvValue(col.label))]
          .concat(
            this.rows.map((row) =>
              this.columns
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
      },
    },
    mounted() {
      this.getTopClients();
    },
  };
</script>