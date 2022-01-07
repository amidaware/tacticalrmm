<template>
<<<<<<< HEAD

  <div class="q-pb-md q-pl-md q-gutter-sm">
    <q-breadcrumbs>
      <q-breadcrumbs-el icon="home" class="text-black" />
      <q-breadcrumbs-el class="text-black" :label="organizationName" />
      <q-breadcrumbs-el class="text-black" label="Overview" />
    </q-breadcrumbs>
  </div>
=======
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
  <q-scroll-area style="height: 230px">
    <q-inner-loading :showing="uplinksLoading" color="primary" />
    <div class="q-pb-md row justify-center q-gutter-md">
      <q-card flat bordered class="my-card bg-grey-1" v-for="device in uplinks">
        <q-card-section>
          <div class="text-h6">
            {{ device.model }}
          </div>
          <div class="text-caption">
            {{ device.serial }}
          </div>
        </q-card-section>
        <q-card-section>
          <div v-for="uplink in device.uplinks">
            <span v-if="uplink.ip">{{ uplink.interface }} - {{ uplink.ip }}

              <q-icon v-if="uplink.status == 'active' || uplink.status == 'ready'" name="brightness_1"
                color="positive" />
              <q-icon v-else name="brightness_1" color="negative" />
            </span>
            <span v-else>{{ uplink.interface }}

              <q-icon v-if="uplink.status == 'active' || uplink.status == 'ready'" name="brightness_1"
                color="positive" />
              <q-icon v-else name="brightness_1" color="negative" />
            </span>
          </div>
        </q-card-section>
        <q-separator />
        <q-card-section class="text-caption text-weight-light">Reported at: {{ device.lastReportedAt }}
        </q-card-section>
      </q-card>
    </div>
  </q-scroll-area>
  <q-table class="q-pt-md q-mb-xl" v-model:pagination="pagination" row-key="name" :rows="rows" :columns="columns"
    :loading="isLoading">
    <template v-slot:loading v-model="isLoading">
      <q-inner-loading showing color="primary" />
    </template>
    <template v-slot:top-left>
      <q-btn flat dense @click="getOverview(timespan.value)" icon="refresh" />
      <q-btn-dropdown no-caps flat :label="timespan.label">
        <q-list>
          <q-item clickable v-close-popup no-caps @click="getOverview(86400)">
            <q-item-section>
              <q-item-label>Over the past day</q-item-label>
            </q-item-section>
          </q-item>
          <q-item clickable v-close-popup no-caps @click="getOverview(604800)">
            <q-item-section>
              <q-item-label> Over the past week </q-item-label>
            </q-item-section>
          </q-item>
          <q-item clickable v-close-popup @click="getOverview(2592000)">
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
                    <q-btn label="OK" color="primary" flat @click="getOverview(dateRange)" v-close-popup />
                  </div>
                </q-date>
              </q-popup-proxy>
            </q-item-section>
          </q-item>
        </q-list>
      </q-btn-dropdown>
      <span class="text-h6">{{ totalClients }} </span>
      <span class="q-px-sm text-weight-light">clients,</span><span class="text-h6"> {{ totalDevicesUsage }}</span>
      <span class="q-pl-sm text-weight-light">transferred</span>
    </template>
    <template v-slot:body="props">
      <q-tr :props="props">
        <q-td key="name" :props="props">
          {{ props.row.name }}
        </q-td>
        <q-td key="model" :props="props">
          {{ props.row.model }}
        </q-td>

        <q-td key="type" :props="props">
          {{ props.row.type }}
        </q-td>
        <q-td key="usage" :props="props">
          {{ props.row.usage }}
        </q-td>
        <q-td key="percentage" :props="props">
          {{ (props.row.percentage * 100).toFixed(2) }}%
          <q-linear-progress :value="props.row.percentage" />
        </q-td>
        <q-td key="clientCount" :props="props">
          {{ props.row.clientCount.total }}
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
      name: "name",
      required: true,
      label: "Name",
      align: "left",
      field: (row) => row.name,
      format: (val) => `${val}`,
      sortable: true,
    },
    {
      name: "model",
      align: "left",
      label: "Model",
      field: "model",
      sortable: true,
    },

    {
      name: "type",
      align: "left",
      label: "Type",
      field: "type",
      sortable: true,
    },

    {
      name: "usage",
      align: "left",
      label: "Usage",
      field: "usage",
      sortable: true,
    },
    {
      name: "percentage",
      align: "left",
      label: "% Used",
      field: "percentage",
      sortable: true,
    },
    {
      name: "clientCount",
      align: "left",
      label: "Clients",
      field: "clientCount",
      sortable: true,
    },
  ];

  export default {
    name: "Overview",
    props: ["organizationID", "organizationName"],
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
        uplinks: ref([]),
        timespan: ref({ label: "Over the past day", value: 86400 }),
        time: ref(),
        totalClients: ref(0),
        totalDevicesUsage: ref(0),
        dateOptions: ref([]),
        dateRange: ref(""),
        updateProxy: ref(""),
        uplinksLoading: ref(false)
      };
    },
    methods: {
      getOverview(time) {
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
          .get(`/meraki/` + this.organizationID + `/devices_summary/` + url + `/`)
          .then(r => {
            this.rows = [];
            this.totalDevicesUsage = 0;
            this.totalClients = 0;

            for (let obj of r.data) {
              if (obj.name !== "Unknown") {
                this.totalDevicesUsage += obj.usage.total;

                let orgDevice = {
                  name: obj.name,
                  model: obj.model,
                  serial: obj.serial,
                  type: obj.productType,
                  usage:
                    obj.usage.total > 1024 && obj.usage.total < 1000000
                      ? (obj.usage.total / 1000).toFixed(2) + " GB"
                      : obj.usage.total > 1000000
                        ? (obj.usage.total / 1000000).toFixed(2) + " TB"
                        : obj.usage.total.toFixed(0) + " MB",
                  percentage: obj.usage.percentage / 100,
                  clientCount: obj.clients.counts,
                };
                this.totalClients += orgDevice.clientCount.total;

                this.rows.push(orgDevice);
              }
            }
            for (let i = 0; i < 30; i++) {
              let newDate = date.subtractFromDate(new Date(), { days: i });
              let formattedDate = date.formatDate(newDate, "YYYY/MM/DD");
              this.dateOptions.push(formattedDate);
            }
            if (this.totalDevicesUsage > 1000000) {
              this.totalDevicesUsage =
                (this.totalDevicesUsage / 1000000).toFixed(2) + " TB";
            } else if (this.totalDevicesUsage > 999) {
              this.totalDevicesUsage = (this.totalDevicesUsage / 1000).toFixed(2) + " GB";
            } else {
              this.totalDevicesUsage.toFixed(2) + " MB";
            }
            this.isLoading = false;
          })
          .catch(e => {

          });
      },
      getUplinks() {
        this.uplinksLoading = true;
        axios
          .get(`/meraki/` + this.organizationID + `/networks/uplinks/`)
          .then(r => {
            this.uplinks = [];
            for (let obj of r.data) {
              let uplink = {
                lastReportedAt: date.formatDate(
                  obj.lastReportedAt,
                  "YYYY-MM-DD @ hh:MM aa"
                ),
                model: obj.model,
                networkID: obj.networkId,
                serial: obj.serial,
                uplinks: obj.uplinks,
              };
              this.uplinks.push(uplink);
            }
            this.uplinksLoading = false;
          })
          .catch(e => {

          });
      },
    },
    mounted() {
      this.getOverview();
      this.getUplinks();
    },
  };
</script>