<template>
    <q-card flat class="q-mb-sm">
        <div>
            <q-btn
                flat
                dense
                @click="getUplinks(); timespan.label = 'for the last day'; timespan.value = 86400"
                icon="refresh"
                label="Summary"
            />
        </div>
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
            <q-table
                class="q-pt-md q-mb-xl"
                :pagination="pagination"
                row-key="networkId"
                :rows="rows"
                :columns="columns"
                :loading="tableLoading"
            >
                <template v-slot:top-left>
                    <div>
                        <q-btn
                            flat
                            dense
                            @click="timespan.label = 'for the last day'; timespan.value = 86400; getOverview()"
                            icon="refresh"
                            label="Overview"
                        />
                    </div>
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
        </div>
        <div class="col-5">
            <div class="row">
                <div class="col-12">
                    <q-card class="q-mx-sm">
                        <q-card-section class="text-center">
                            <span class="text-weight-light">Overview Total</span>
                            <div>
                                <span class="text-h6">{{ totalClients }}</span>
                                <span class="text-weight-normal q-mx-sm">clients,</span>
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
                                            @click="timespan.label = 'for the last day'; timespan.value = 86400; getOverview()"
                                        >
                                            <q-item-section>
                                                <q-item-label>for the last day</q-item-label>
                                            </q-item-section>
                                        </q-item>
                                        <q-item
                                            clickable
                                            v-close-popup
                                            no-caps
                                            @click="timespan.label = 'for the last week'; timespan.value = 604800; getOverview()"
                                        >
                                            <q-item-section>
                                                <q-item-label>for the last week</q-item-label>
                                            </q-item-section>
                                        </q-item>
                                        <q-item
                                            clickable
                                            v-close-popup
                                            @click="timespan.label = 'for the last 30 days'; timespan.value = 2592000; getOverview()"
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
                                                    <q-date
                                                        v-model="dateRange"
                                                        :options="dateOptions"
                                                        range
                                                    >
                                                        <div
                                                            class="row items-center justify-end q-gutter-sm"
                                                        >
                                                            <q-btn
                                                                label="Cancel"
                                                                color="primary"
                                                                flat
                                                                v-close-popup
                                                            />
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
                            </div>
                        </q-card-section>
                    </q-card>
                    <q-card class="q-mx-sm q-my-sm">
                        <TopClientsTable
                            :organizationID="organizationID"
                            :organizationName="organizationName"
                        />
                    </q-card>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import { ref, onBeforeMount } from "vue";
import { useQuasar, date } from "quasar";
import TopClientsTable from "@/components/integrations/meraki/organization/TopClientsTable";

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
    // {
    //     name: "model",
    //     align: "left",
    //     label: "Model",
    //     field: "model",
    //     sortable: true,
    // },

    {
        name: "productType",
        align: "left",
        label: "Type",
        field: "productType",
        sortable: true,
    },
    // {
    //     name: "serial",
    //     align: "left",
    //     label: "Serial",
    //     field: "serial",
    //     sortable: true,
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
    components: { TopClientsTable },
    setup(props) {
        const $q = useQuasar();

        const rows = ref([])
        const uplinks = ref("")
        const timespan = ref({ label: "for the last day", value: 86400 })
        const timespanMenu = ref(false)
        const totalClients = ref(null)
        const totalUsage = ref(null)
        const dateOptions = ref([])
        const dateRange = ref("")
        const updateProxy = ref("")
        const tableLoading = ref(false)
        const uplinksLoading = ref(false)

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

        function getUplinks() {
            $q.loading.show({ message: 'Producing a summary of ' + props.organizationName + '...' })

            axios
                .get(`/meraki/` + props.organizationID + `/networks/uplinks/`)
                .then(r => {

                    uplinks.value = r.data

                    getOverview()

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
                .get(`/meraki/` + props.organizationID + `/overview/` + timespan.value.value + `/`)
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
                    $q.loading.hide()
                    tableLoading.value = false
                })
                .catch(e => {

                });
        }

        onBeforeMount(() => {
            getUplinks()

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
            getUplinks,
            getOverview,
        };
    }
}
</script>