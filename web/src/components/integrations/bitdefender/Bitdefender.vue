<template>
    <q-card flat>
        <q-tabs
            v-model="tab"
            dense
            align="left"
            class="text-grey"
            active-color="primary"
            indicator-color="primary"
            no-caps
            narrow-indicator
            inline-label
        >
            <q-tab icon="computer" name="endpoint" label="Endpoint" />
            <q-tab icon="task_alt" name="scanTasks" label="Scan Tasks" />
            <q-tab icon="local_police" name="quarantine" label="Quarantine" />
            <q-tab icon="summarize" name="reports" label="Reports" />
        </q-tabs>
        <q-tab-panels v-model="tab" animated>
            <q-tab-panel name="endpoint" class="q-px-none">
                <q-btn-dropdown label="Actions" flat>
                    <q-list>
                        <q-item clickable v-close-popup @click="getInstallLinks()">
                            <q-item-section>
                                <q-item-label>Get Install Links</q-item-label>
                            </q-item-section>
                        </q-item>
                        <q-item clickable v-close-popup @click="quickScan()">
                            <q-item-section>
                                <q-item-label>Quick Scan</q-item-label>
                            </q-item-section>
                        </q-item>
                        <q-item clickable v-close-popup @click="fullScan()">
                            <q-item-section>
                                <q-item-label>Full Scan</q-item-label>
                            </q-item-section>
                        </q-item>
                    </q-list>
                </q-btn-dropdown>
                <div class="row">
                    <div class="col-5">
                        <q-list>
                            <q-item-section>
                                <q-item-label header>GENERAL</q-item-label>
                            </q-item-section>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Name</q-item-label>
                                </q-item-section>
                                <q-item-section side top>{{ endpoint.name }}</q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>ID</q-item-label>
                                </q-item-section>
                                <q-item-section side top>{{ endpoint.id }}</q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Policy</q-item-label>
                                </q-item-section>
                                <q-item-section side top>{{ endpoint.policy }}</q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Last Seen</q-item-label>
                                </q-item-section>
                                <q-item-section side top>{{ endpoint.lastSeen }}</q-item-section>
                            </q-item>
                            <q-separator inset />
                            <q-item-label header>AGENT</q-item-label>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Product Version</q-item-label>
                                </q-item-section>
                                <q-item-section side top>{{ endpoint.productVersion }}</q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Engine Version</q-item-label>
                                </q-item-section>
                                <q-item-section side top>{{ endpoint.engineVersion }}</q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Last Update</q-item-label>
                                </q-item-section>
                                <q-item-section side top>{{ endpoint.lastUpdated }}</q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Malware Detected</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                    <span>
                                        <q-icon
                                            name="priority_high"
                                            color="negative"
                                            v-if="endpoint.malwareDetected"
                                        />
                                        {{ endpoint.malwareDetected }}
                                    </span>
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Infected</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                    <span>
                                        <q-icon
                                            name="priority_high"
                                            color="negative"
                                            v-if="endpoint.malwareInfected"
                                        />
                                        {{ endpoint.malwareInfected }}
                                    </span>
                                </q-item-section>
                            </q-item>
                            <q-separator inset />
                            <q-item-label header>MODULES</q-item-label>
                            <q-item dense v-for="moduleObj of modules">
                                <q-item-section top>
                                    <q-item-label>{{ moduleObj.label }}</q-item-label>
                                </q-item-section>

                                <q-item-section side top>{{ moduleObj.value }}</q-item-section>
                            </q-item>
                        </q-list>
                    </div>
                    <div class="col-7">
                        <div class="row q-mt-sm">
                            <div class="col-12">
                                <q-card class="q-mx-sm q-mb-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-h6">Risk Score</span>
                                        <q-linear-progress
                                            size="20px"
                                            :value="endpoint.riskScoreValue"
                                            color="negative"
                                        >
                                            <div class="absolute-full flex flex-center">
                                                <q-badge
                                                    color="white"
                                                    text-color="black"
                                                    :label="endpoint.riskScoreLabel + ' - ' + endpoint.impact"
                                                />
                                            </div>
                                        </q-linear-progress>
                                    </q-card-section>
                                </q-card>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-lg-4 col-md-6 col-sm-12 col-xs-12">
                                <q-card class="q-mx-sm q-mb-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-weight-light">Misconfigurations</span>
                                        <div class="text-h6">{{ endpoint.misconfigurations }}</div>
                                    </q-card-section>
                                </q-card>
                            </div>
                            <div class="col-lg-4 col-md-6 col-sm-12 col-xs-12">
                                <q-card class="q-mx-sm q-mb-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-weight-light">App Vulnerabilities</span>
                                        <div class="text-h6">{{ endpoint.appVulnerabilities }}</div>
                                    </q-card-section>
                                </q-card>
                            </div>
                            <div class="col-lg-4 col-md-6 col-sm-12 col-xs-12">
                                <q-card class="q-mx-sm q-mb-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-weight-light">Human Risks</span>
                                        <div class="text-h6">{{ endpoint.humanRisks }}</div>
                                    </q-card-section>
                                </q-card>
                            </div>
                        </div>
                    </div>
                </div>
            </q-tab-panel>
            <q-tab-panel name="scanTasks" class="q-px-none">
                <ScanTasksTab :endpoint="endpoint" />
            </q-tab-panel>
            <q-tab-panel name="quarantine" class="q-px-none">
                <QuarantineTab :endpoint="endpoint" />
            </q-tab-panel>
            <q-tab-panel name="reports" class="q-px-none">
                <ReportsTab :endpoint="endpoint" />
            </q-tab-panel>
        </q-tab-panels>
    </q-card>
</template>

<script>
import axios from "axios";
import { ref, computed, watch, onMounted } from "vue";
import { useQuasar, useDialogPluginComponent, date } from "quasar";
import { notifyError } from "@/utils/notify";
import InstallLinks from "@/components/integrations/bitdefender/modals/InstallLinks";
import ScanEndpoint from "@/components/integrations/bitdefender/modals/ScanEndpoint";
import QuarantineTab from "@/components/integrations/bitdefender/QuarantineTab";
import ScanTasksTab from "@/components/integrations/bitdefender/ScanTasksTab";
import ReportsTab from "@/components/integrations/bitdefender/ReportsTab"

export default {
    name: "Bitdefender",
    emits: [...useDialogPluginComponent.emits],
    props: ['agent'],
    components: { InstallLinks, ScanTasksTab, QuarantineTab, ReportsTab },
    setup(props) {
        const { dialogRef, onDialogHide } = useDialogPluginComponent();
        const $q = useQuasar();

        const tab = ref("")
        const tacticalAgentMacs = ref([])
        const bitdefenderEndpoints = ref([])
        const bitdefenderEndpointMacs = ref([])
        const bitdefenderEndpoint = ref([])
        const endpoint = ref([])
        const modules = ref([])

        async function getBitdefenderEndpoints() {
            $q.loading.show()
            const bitdefenderEndpointsArray = [];
            const r = await axios.get(`/bitdefender/endpoints/`, { params: { pageNumber: 1 } });

            for (let i = 0; i < r.data.result.pagesCount; i++) {
                let nextPage = i + 1
                bitdefenderEndpointsArray.push(axios.get(`/bitdefender/endpoints/`, { params: { pageNumber: nextPage } }));
            };

            let resolvedbitdefenderEndpoints = await Promise.all(bitdefenderEndpointsArray)
            for (let i = 0; i < resolvedbitdefenderEndpoints.length; i++) {
                bitdefenderEndpoints.value.push(...resolvedbitdefenderEndpoints[i].data.result.items)
            }

            for (let i = 0; i < props.agent.wmi_detail.network_adapter.length; i++) {
                for (let obj of props.agent.wmi_detail.network_adapter[i]) {
                    const macStr = String(obj.MACAddress)
                    const macs = macStr.replaceAll(":", "").toLowerCase()
                    tacticalAgentMacs.value.push(macs)
                }
            }
            for (let i = 0; i < bitdefenderEndpoints.value.length; i++) {
                bitdefenderEndpointMacs.value.push(bitdefenderEndpoints.value[i].details.macs[0])
                const macMatch = tacticalAgentMacs.value.filter(element => bitdefenderEndpointMacs.value.includes(element))
                if (macMatch.length > 0) {
                    bitdefenderEndpoint.value = bitdefenderEndpoints.value[i]
                    tab.value = 'endpoint'
                    getBitdefenderEndpoint()
                    return;
                }
            }
            $q.loading.hide()
            notifyError("Could not find the " + props.agent.hostname + " endpoint with the same MAC address in Bitdefender GravityZone")
            getInstallLinks()
        }

        function getBitdefenderEndpoint() {
            axios
                .get(`/bitdefender/endpoint/` + bitdefenderEndpoint.value.id + `/`)
                .then(r => {
                    let riskScore = r.data.result.riskScore ? Number(r.data.result.riskScore.value.replace('%', '') / 100) : 0
                    endpoint.value = {
                        id: r.data.result.id,
                        name: r.data.result.name,
                        policy: r.data.result.policy.name,
                        lastSeen: date.formatDate(r.data.result.lastSeen, 'ddd, MMM D, YYYY @ hh:mm A'),
                        productVersion: r.data.result.agent.productVersion,
                        engineVersion: r.data.result.agent.engineVersion,
                        lastUpdated: date.formatDate(r.data.result.agent.lastUpdate, 'ddd, MMM D, YYYY @ hh:mm A'),
                        malwareDetected: r.data.result.malwareStatus.detection,
                        malwareInfected: r.data.result.malwareStatus.infected,
                        riskScoreLabel: r.data.result.riskScore ? computed(() => (riskScore * 100).toFixed(0) + '%') : 0,
                        riskScoreValue: r.data.result.riskScore ? Number(r.data.result.riskScore.value.replace('%', '') / 100) : 0,
                        impact: r.data.result.riskScore ? r.data.result.riskScore.impact : "N/A",
                        misconfigurations: r.data.result.riskScore ? r.data.result.riskScore.misconfigurations : "N/A",
                        appVulnerabilities: r.data.result.riskScore ? r.data.result.riskScore.appVulnerabilities : "N/A",
                        humanRisks: r.data.result.riskScore ? r.data.result.riskScore.humanRisks : "N/A",
                    }
                    for (const [key, value] of Object.entries(r.data.result.modules)) {
                        let obj = {
                            label: key,
                            value: value
                        }
                        modules.value.push(obj)
                        $q.loading.hide()
                    }
                })
                .catch(e => {
                    console.log(e)
                });
        }

        function getInstallLinks() {
            $q.dialog({
                component: InstallLinks,
                componentProps: {
                    endpoint: endpoint.value
                }
            })
        }

        function quickScan() {
            $q.dialog({
                component: ScanEndpoint,
                componentProps: {
                    scanType: 'quick',
                    endpoint: endpoint.value
                }
            })
        }

        function fullScan() {
            $q.dialog({
                component: ScanEndpoint,
                componentProps: {
                    scanType: 'full',
                    endpoint: endpoint.value
                }
            })
        }

        onMounted(() => {
            getBitdefenderEndpoints()
        });

        return {
            tab,
            endpoint,
            modules,
            getInstallLinks,
            quickScan,
            fullScan,
            // quasar dialog
            dialogRef,
            onDialogHide,
        };
    },
};
</script>