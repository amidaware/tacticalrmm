<template>
  <q-scroll-area style="height: 230px">

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
  <q-table class="q-pt-md q-mb-xl" v-model:pagination="pagination" row-key="networkId" :rows="rows" :columns="columns">
    <template v-slot:top-left>
      <q-btn flat dense @click="timespan.value = 86400;getOverview()" icon="refresh" class="q-mb-sm q-mr-md"/>
      <span class="text-h6">{{ totalClients }} </span>
      <span class="q-px-sm">clients and</span><span class="text-h6"> {{ totalUsage }}</span>
      <span class="q-pl-sm">transferred</span>
      <q-btn-dropdown no-caps flat :label="timespan.label">
        <q-list>
          <q-item clickable v-close-popup no-caps @click="timespan.label='for the past day';timespan.value = 86400;getOverview()">
            <q-item-section>
              <q-item-label>for the past day</q-item-label>
            </q-item-section>
          </q-item>
          <q-item clickable v-close-popup no-caps @click="timespan.label='for the past week';timespan.value = 604800;getOverview()">
            <q-item-section>
              <q-item-label> for the past week </q-item-label>
            </q-item-section>
          </q-item>
          <q-item clickable v-close-popup @click="timespan.label='for the past 30 days';timespan.value = 2592000;getOverview(2592000)">
            <q-item-section>
              <q-item-label>for the past 30 days</q-item-label>
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
    </template>
    <template v-slot:body="props">
      <q-tr :props="props">
        <q-td key="name" :props="props">
          {{ props.row.name }}
        </q-td>
        <q-td key="model" :props="props">
          {{ props.row.model }}
        </q-td>

        <q-td key="productType" :props="props">
          {{ props.row.productType }}
        </q-td>
        <q-td key="serial" :props="props">
          {{ props.row.serial }}
        </q-td>
        <q-td key="usageTotal" :props="props">
          {{ props.row.usage.total }}
        </q-td>
        <q-td key="usagePercentage" :props="props">
          {{ (props.row.usage.percentage).toFixed(0) }}%
          <q-linear-progress :value="props.row.usage.progress" />
        </q-td>
        <q-td key="clients" :props="props">
          {{ props.row.clients }}
        </q-td>
      </q-tr>
    </template>
  </q-table>
</template>

<script>
  import axios from "axios";
  import { ref, computed, onMounted, onBeforeMount } from "vue";
  import { useMeta, useQuasar, useDialogPluginComponent, date } from "quasar";
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
      name: "model",
      align: "left",
      label: "Model",
      field: "model",
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
      name: "serial",
      align: "left",
      label: "Serial",
      field: "serial",
      sortable: true,
    },
    {
      name: "usageTotal",
      align: "left",
      label: "Usage",
      field: "usageTotal",
      sortable: true,
    },
    {
      name: "usagePercentage",
      align: "left",
      label: "% Used",
      field: "usagePercentage",
      sortable: true,
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
    name: "OverviewTable",
    props: ["organizationID", "organizationName"],
    setup(props) {
      const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
      const $q = useQuasar();

      const rows = ref([])
      const uplinks = ref([])
      const timespan = ref({ label: "for the past day", value: 86400 })
      const time = ref()
      const totalClients = ref(null)
      const totalUsage = ref(null)
      const dateOptions = ref([])
      const dateRange = ref("")
      const updateProxy = ref("")

      function formatUsage(usage, decimals = 2) {
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

      function getOverview() {
        $q.loading.show({ message: 'Producing an overview of the organization...' })
        axios
          .get(`/meraki/` + props.organizationID + `/devices_summary/` + timespan.value.value + `/`)
          .then(r => {
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
            getUplinks()

          })
          .catch(e => {

          });
      }

      function getUplinks() {
        axios
          .get(`/meraki/` + props.organizationID + `/networks/uplinks/`)
          .then(r => {
            uplinks.value = [];
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
              uplinks.value.push(uplink);
            }
            $q.loading.hide()
          })
          .catch(e => {

          });
      }

      onBeforeMount(() => {
        getOverview()
        getUplinks()
      })

      return {
        pagination: {
          rowsPerPage: 10,
          sortBy: "percentage",
          descending: true,
        },
        rows,
        columns,
        uplinks,
        timespan,
        time,
        totalClients,
        totalUsage,
        dateOptions,
        dateRange,
        updateProxy,
        getOverview,
      };
    }
  }
</script>