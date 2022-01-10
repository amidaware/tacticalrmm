<template>

  <q-table :rows="rows" :columns="columns" row-key="name" v-model:pagination="pagination"
    :visible-columns="applicationTrafficColumnsVisible" :loading="isLoading" :filter="filter">
    <template v-slot:loading v-model="isLoading">
      <q-inner-loading showing color="primary" />
    </template>
    <template v-slot:top-right>
      <q-input outlined clearable dense debounce="300" v-model="filter" label="Search">
        <template v-slot:prepend>
          <q-icon name="search" />
        </template>
      </q-input>
    </template>
    <template v-slot:top-left>
      <q-btn flat dense @click="getApplicationTraffic(timespan.value)" icon="refresh" />
      <q-btn-dropdown no-caps flat :label="timespan.label">
        <q-list>
          <q-item clickable v-close-popup no-caps @click="getApplicationTraffic(7200)">
            <q-item-section>
              <q-item-label>Over the past 2 hours</q-item-label>
            </q-item-section>
          </q-item>
          <q-item clickable v-close-popup no-caps @click="getApplicationTraffic(86400)">
            <q-item-section>
              <q-item-label>Over the past day</q-item-label>
            </q-item-section>
          </q-item>
          <q-item clickable v-close-popup no-caps @click="getApplicationTraffic(604800)">
            <q-item-section>
              <q-item-label> Over the past week </q-item-label>
            </q-item-section>
          </q-item>
          <q-item clickable v-close-popup @click="getApplicationTraffic(2592000)">
            <q-item-section>
              <q-item-label>Over the past 30 days</q-item-label>
            </q-item-section>
          </q-item>
          <q-item clickable>
            <q-item-section v-ripple>
              <q-item-label>Custom date</q-item-label>
              <q-popup-proxy @before-show="updateProxy" transition-show="scale" transition-hide="scale">
                <q-date v-model="date" :options="dateOptions">
                  <div class="row items-center justify-end q-gutter-sm">
                    <q-btn label="Save Date" color="white" class="text-black" @click="getApplicationTraffic(date)"
                      v-close-popup />
                    <q-btn label="Cancel" flat color="white" class="text-black q-ml-md" v-close-popup />
                  </div>
                </q-date>
              </q-popup-proxy>
            </q-item-section>
          </q-item>
        </q-list>
      </q-btn-dropdown>
      <span class="text-h6">{{ totalTraffic }}</span>
      <span class="q-px-sm text-weight-light">(
        <q-icon name="arrow_downward" />{{ totalTrafficRecv }},
        <q-icon name="arrow_upward" />{{ totalTrafficSent }}) transferred
      </span>
    </template>
    <template v-slot:body="props">
      <q-tr :props="props">
        <q-td key="application" :props="props">
          <span class="text-caption">{{ props.row.application }}</span>
        </q-td>
        <q-td key="destination" :props="props">
          <q-btn type="a" no-caps class="q-pa-none text-caption text-weight-bold" flat
            :href="'https://viewdns.info/whois/?domain=' + props.row.destination" target="_blank"
            :label="props.row.destination" />
        </q-td>
        <q-td key="protocol" :props="props">
          <span class="text-caption">{{ props.row.protocol }}</span>
        </q-td>
        <q-td key="port" :props="props">
          <span class="text-caption">{{ props.row.port }}</span>
        </q-td>
        <q-td key="totalUsage" :props="props">
          <span class="text-caption">{{ props.row.totalUsage }}</span>
        </q-td>
        <q-td key="totalUsageSort" :props="props">
          <span class="text-caption">{{ props.row.totalUsageSort }}</span>
        </q-td>
        <q-td key="recv" :props="props">
          <span class="text-caption">{{ props.row.recv }}</span>
        </q-td>
        <q-td key="sent" :props="props">
          <span class="text-caption">{{ props.row.sent }}</span>
        </q-td>
        <q-td key="flows" :props="props">
          <span class="text-caption">{{ props.row.flows }}</span>
        </q-td>
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
  import { ref } from "vue";
  import { date } from "quasar";
  import axios from "axios";

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
      name: "totalUsageSort",
      label: "Total Usage Sort",
      field: "totalUsageSort",
      align: "left",
      sortable: true,
    },
    {
      name: "totalUsage",
      label: "Usage",
      field: "totalUsage",
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
    data() {
      return {
        pagination: {
          rowsPerPage: 10,
          sortBy: "totalUsageSort",
          descending: true,
        },
        columns,
        rows: [],
        applicationTrafficColumnsVisible: ref([
          "application",
          "destination",
          "protocol",
          "port",
          "totalUsage",
          "percentage",
          "numClients",
          "activeTime",
          "flows",
        ]),
        timespan: { label: "Over the past 2 hours", value: 7200 },
        isLoading: ref(false),
        totalTraffic: 0,
        totalTrafficObj: 0,
        traffic: 0,
        trafficObj: 0,
        perTrafficObj: 0,
        percentUsedObj: 0,
        clientTraffic: "",
        totalClients: 0,
        totalTrafficRecv: 0,
        totalTrafficSent: 0,
        filter: ref(""),
        dateOptions: ref([]),
        date: ref(""),
        dates: ref([]),
        updateProxy: ref(""),
        save: ref(""),
        time: ref(),
        timespanDropdown: ref(false),
      };
    },
    methods: {
      getApplicationTraffic(time) {
        this.isLoading = true;
        let url = null;
        if (time === 7200) {
          this.timespan.label = "Over the past 2 hours";
          this.timespan.value = 7200;
        } else if (time === 86400) {
          this.timespan.label = "Over the past day";
          this.timespan.value = 86400;
        } else if (time === 604800) {
          this.timespan.label = "Over the past week";
          this.timespan.value = 604800;
        } else if (time === 2592000) {
          this.timespan.label = "Over the past 30 days";
          this.timespan.value = 2592000;
        }
        if (typeof time === "string" && typeof time !== null) {
          const t0 = date.formatDate(time, "YYYY-MM-DDT00:00:00.000Z");
          const formattedDate = date.formatDate(time, "MMM DD, YYYY HH:MM aa");
          this.timespan.label = "After: " + formattedDate;

          url = "t0=" + t0;
        } else if (typeof time === "number" && time !== null) {
          url = time;
        } else {
          url = 7200;
        }
        axios
          .get(`/meraki/` + this.networkID + `/applications/traffic/` + url + `/`)
          .then(r => {
            this.totalTrafficObj = 0;
            this.totalTrafficRecvObj = 0;
            this.totalTrafficSentObj = 0;
            this.totalTraffic = 0;
            this.totalTrafficRecv = 0;
            this.totalTrafficSent = 0;
            this.perAppTraffic = 0;

            this.rows = [];

            for (let traffic of r.data) {
              let trafficObj = {
                application: traffic.application,
                destination: traffic.destination === null ? "-" : traffic.destination,
                protocol: traffic.protocol,
                port: traffic.port,
                totalUsage:
                  traffic.recv + traffic.sent > 1048576 &&
                    traffic.recv + traffic.sent < 1073741824
                    ? ((traffic.recv + traffic.sent) / 1048576).toFixed(2) + " GB"
                    : traffic.recv + traffic.sent > 1024 &&
                      traffic.recv + traffic.sent < 1048576
                      ? ((traffic.recv + traffic.sent) / 1024).toFixed(1) + " MB"
                      : traffic.recv + traffic.sent < 1024
                        ? ((traffic.recv + traffic.sent) / 1024).toFixed(0) + " KB"
                        : "",
                totalUsageSort: traffic.recv + traffic.sent,
                numClients: traffic.numClients,
                activeTime:
                  traffic.activeTime / 60 / 60 > 24
                    ? (traffic.activeTime / 60 / 60 / 24).toFixed(1) + " days"
                    : traffic.activeTime / 60 > 60
                      ? (traffic.activeTime / 60 / 60).toFixed(1) + " hours"
                      : traffic.activeTime / 60 < 60
                        ? (traffic.activeTime / 60).toFixed(0) + " minutes"
                        : "",
                flows: traffic.flows,
              };
              this.totalTrafficObj += trafficObj.totalUsageSort;
              this.totalTrafficRecvObj += traffic.recv;
              this.totalTrafficSentObj += traffic.sent;
              this.rows.push(trafficObj);
            }
            this.totalTrafficObj > 1073741824
              ? (this.totalTraffic = (this.totalTrafficObj / 1073741824).toFixed(2) + " TB")
              : this.totalTrafficObj > 1048576 && this.totalTrafficObj < 1073741824
                ? (this.totalTraffic = (this.totalTrafficObj / 1048576).toFixed(2) + " GB")
                : this.totalTrafficObj > 1024 && this.totalTrafficObj < 1048576
                  ? (this.totalTraffic = (this.totalTrafficObj / 1024).toFixed(1) + " MB")
                  : this.totalTrafficObj < 1024
                    ? (this.totalTraffic = (this.totalTrafficObj / 1024).toFixed(0) + " KB")
                    : "";

            this.totalTrafficRecvObj > 1073741824
              ? (this.totalTrafficRecv =
                (this.totalTrafficRecvObj / 1073741824).toFixed(2) + " TB")
              : this.totalTrafficRecvObj > 1048576 && this.totalTrafficRecvObj < 1073741824
                ? (this.totalTrafficRecv =
                  (this.totalTrafficRecvObj / 1048576).toFixed(2) + " GB")
                : this.totalTrafficObj > 1024 && this.totalTrafficRecvObj < 1048576
                  ? (this.totalTrafficRecv =
                    (this.totalTrafficRecvObj / 1024).toFixed(1) + " MB")
                  : this.totalTrafficRecvObj < 1024
                    ? (this.totalTrafficRecv =
                      (this.totalTrafficRecvObj / 1024).toFixed(0) + " KB")
                    : "";
            this.totalTrafficSentObj > 1073741824
              ? (this.totalTrafficSent =
                (this.totalTrafficSentObj / 1073741824).toFixed(2) + " TB")
              : this.totalTrafficSentObj > 1048576 && this.totalTrafficSentObj < 1073741824
                ? (this.totalTrafficSent =
                  (this.totalTrafficSentObj / 1048576).toFixed(2) + " GB")
                : this.totalTrafficObj > 1024 && this.totalTrafficSentObj < 1048576
                  ? (this.totalTrafficSent =
                    (this.totalTrafficSentObj / 1024).toFixed(1) + " MB")
                  : this.totalTrafficSentObj < 1024
                    ? (this.totalTrafficSent =
                      (this.totalTrafficSentObj / 1024).toFixed(0) + " KB")
                    : "";
            for (let i = 0; i < 30; i++) {
              let newDate = date.subtractFromDate(new Date(), { days: i });
              let formattedDate = date.formatDate(newDate, "YYYY/MM/DD");
              this.dateOptions.push(formattedDate);
            }
            this.isLoading = false;
          })
          .catch(e => {

          });
      },
    },
    mounted() {
      this.getApplicationTraffic(this.timespan.value);
    },
  };
</script>