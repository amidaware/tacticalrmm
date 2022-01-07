<template>
<<<<<<< HEAD
  <div class="q-pb-md q-pl-md q-gutter-sm">
    <q-breadcrumbs>
      <q-breadcrumbs-el icon="home" class="text-black" />
      <q-breadcrumbs-el class="text-black" :label="organizationName" />
      <q-breadcrumbs-el class="text-black" :label="networkName" />
      <q-breadcrumbs-el class="text-black" label="Traffic" />
      <q-breadcrumbs-el label="Clients" />
    </q-breadcrumbs>
  </div>
=======
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
  <div v-if="isLoaded">
    <MerakiClientModal v-model="clientModalVisible" @close="clientModalClose"
      :maximized="$q.platform.is.mobile ? clientModalVisible : false" :networkID="networkID" :clientID="clientID" />
  </div>
  <q-table :rows="rows" :columns="columns" row-key="id" v-model:pagination="pagination" :loading="isLoading"
    :filter="filter" :visible-columns="visibleColumns">
    <template v-slot:loading v-model="isLoading">
      <q-inner-loading showing color="primary" />
    </template>
    <template v-slot:top-left>
      <q-btn flat dense @click="getClientTraffic(timespan.value)" icon="refresh" />
      <q-btn-dropdown no-caps flat :label="timespan.label">
        <q-list>
          <q-item clickable v-close-popup no-caps @click="getClientTraffic(7200)">
            <q-item-section>
              <q-item-label>Over the past 2 hours</q-item-label>
            </q-item-section>
          </q-item>
          <q-item clickable v-close-popup no-caps @click="getClientTraffic(86400)">
            <q-item-section>
              <q-item-label>Over the past day</q-item-label>
            </q-item-section>
          </q-item>
          <q-item clickable v-close-popup no-caps @click="getClientTraffic(604800)">
            <q-item-section>
              <q-item-label> Over the past week </q-item-label>
            </q-item-section>
          </q-item>
          <q-item clickable v-close-popup @click="getClientTraffic(2592000)">
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
                    <q-btn label="Save Date" color="white" class="text-black" @click="getClientTraffic(date)"
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
    <template v-slot:top-right>
      <q-input outlined clearable dense debounce="300" v-model="filter" label="Search">
        <template v-slot:prepend>
          <q-icon name="search" />
        </template>
      </q-input>
    </template>
    <template v-slot:body="props">
      <q-tr :props="props">
        <q-td key="status" :props="props">
          <q-icon v-if="props.row.status == 'Online'" name="brightness_1" color="positive" />
          <q-icon v-else name="brightness_1" color="negative" />
        </q-td>
        <q-td key="id" :props="props">
          <span class="text-caption">{{ props.row.id }}</span>
        </q-td>
        <q-td key="user" :props="props">
          <span class="text-caption">{{ props.row.user }}</span>
        </q-td>
        <q-td key="description" :props="props">
          <span class="text-caption">{{ props.row.description }}</span>
        </q-td>
        <q-td key="totalUsage" :props="props">
          <span class="text-caption">{{ props.row.totalUsage }}</span>
        </q-td>
        <q-td key="firstSeen" :props="props">
          <span class="text-caption">{{ props.row.firstSeen }}</span>
        </q-td>
        <q-td key="lastSeen" :props="props">
          <span class="text-caption">{{ props.row.lastSeen }}</span>
        </q-td>
        <q-td key="percentage" :props="props">
          <span class="text-caption">{{ props.row.percentUsed.fixed }}</span>
          <q-linear-progress :value="props.row.percentUsed.notFixed" color="positive">
          </q-linear-progress>
        </q-td>
        <q-td key="totalUsageSort" :props="props">
          <span class="text-caption">{{ props.row.totalUsageSort }}</span>
        </q-td>
        <q-td key="os" :props="props">
          <span class="text-caption">{{ props.row.os }}</span>
        </q-td>
        <q-td key="ip" :props="props">
          <span class="text-caption">{{ props.row.ip }}</span>
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
      name: "status",
      label: "Status",
      align: "left",
      field: (row) => row.status,
      format: (val) => `${val}`,
      sortable: true,
      required: true,
    },
    {
      name: "id",
      align: "left",
      label: "ID",
      field: "id",
      sortable: true,
      required: true,
    },

    {
      name: "user",
      align: "left",
      label: "User",
      field: "user",
      sortable: true,
      required: true,
    },
    {
      name: "description",
      align: "left",
      label: "Description",
      field: "description",
      sortable: true,
      required: true,
    },
    {
      name: "totalUsage",
      label: "Usage",
      field: "totalUsage",
      align: "left",
      sortable: false,
      required: true,
    },
    {
      name: "firstSeen",
      label: "First Seen",
      field: "firstSeen",
      align: "left",
      sortable: true,
      required: true,
    },
    {
      name: "lastSeen",
      label: "Last Seen",
      field: "lastSeen",
      align: "left",
      sortable: true,
      required: true,
    },
    {
      name: "totalUsageSort",
      label: "Total Usage Sort",
      field: "totalUsageSort",
      align: "left",
      sortable: true,
    },

    {
      name: "percentage",
      label: "% Usage",
      field: "percentage",
      align: "left",
      sortable: false,
    },

    {
      name: "os",
      label: "OS",
      field: "os",
      align: "left",
      sortable: true,
      required: true,
    },
    {
      name: "ip",
      label: "IPv4",
      field: "ip",
      align: "left",
      sortable: true,
      required: true,
    },
  ];

  export default {
    name: "ClientTrafficTable",
    components: {  },
    props: ["organizationName", "networkID", "networkName"],
    data() {
      return {
        pagination: {
          rowsPerPage: 10,
          sortBy: "totalUsageSort",
          descending: true,
        },
        visibleColumns: ref([
          "status",
          "id",
          "description",
          "firstSeen",
          "lastseen",
          "user",
          "totalUsage",
          "manufacturer",
          "os",
          "ip",
        ]),
        timespan: { label: "Over the past 2 hours", value: 7200 },
        columns,
        rows: [],
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
        date: "",
        dates: ref([]),
        updateProxy: "",
        save: "",
        client: "",
        clientID: "",
        clientPolicy: "",
        clientModalVisible: false,
        isLoaded: false,
        timespanDropdown: false,
      };
    },
    methods: {
      getClientTraffic(time) {
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
          .get(`/meraki/` + this.networkID + `/clients/traffic/` + url + `/`)
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
                status: traffic.status,
                id: traffic.id,
                description: traffic.description ? traffic.description : traffic.mac,
                user: traffic.user,
                firstSeen: date.formatDate(traffic.firstSeen, "MMM DD, YYYY @ hh:MM aa"),
                lastSeen: date.formatDate(traffic.lastSeen, "MMM DD, YYYY @ hh:MM aa"),
                totalUsage:
                  traffic.usage.total > 1048576 && traffic.usage.total < 1073741824
                    ? (traffic.usage.total / 1048576).toFixed(2) + " GB"
                    : traffic.usage.total > 1024 && traffic.usage.total < 1048576
                      ? (traffic.usage.total / 1024).toFixed(1) + " MB"
                      : traffic.usage.total < 1024
                        ? (traffic.usage.total / 1024).toFixed(0) + " KB"
                        : "-",
                percentUsed: {
                  fixed: this.percentUsedObj.toFixed(1) + "%",
                  notFixed: traffic.usage.total / this.totalTrafficObj,
                },
                totalUsageSort: traffic.usage.total,
                os: traffic.os,
                ip: traffic.ip,
              };
              this.totalTrafficObj += trafficObj.totalUsageSort;
              this.totalTrafficRecvObj += traffic.usage.recv;
              this.totalTrafficSentObj += traffic.usage.sent;
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
      getClientModal(clientID) {
        this.isLoading = true;
        this.clientID = clientID;
        this.isLoaded = true;
        this.clientModalVisible = true;
        this.isLoading = false;
      },
      clientModalClose() {
        this.clientModalVisible = false;
        this.isLoaded = false;
      },
      clientModalOpen() {
        this.clientModalVisible = true;
      },
    },
    mounted() {
      this.getClientTraffic(this.timespan.value);
    },
  };
</script>