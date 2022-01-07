<template>
    <q-card flat>
        <q-tabs v-model="tab" dense align="left" class="text-grey" active-color="primary" indicator-color="primary"
            no-caps narrow-indicator inline-label>
            <q-tab icon="computer" name="asset" label="Asset" />
            <q-tab icon="save" name="licenses" label="Licenses" />
            <q-tab icon="build" name="maintenances" label="Maintenances" />
        </q-tabs>
        <q-tab-panels v-model="tab" animated>
            <q-tab-panel name="asset">
                <q-btn-dropdown label="Actions" flat>
                    <q-list>
                        <q-item clickable v-close-popup @click="scanEndpointConfirm('quick')">
                            <q-item-section>
                                <q-item-label>Checkout</q-item-label>
                            </q-item-section>
                        </q-item>

                        <q-item clickable v-close-popup @click="scanEndpointConfirm('full')">
                            <q-item-section>
                                <q-item-label>Checkin</q-item-label>
                            </q-item-section>
                        </q-item>

                        <q-item clickable v-close-popup @click="scanEndpointConfirm('full')">
                            <q-item-section>
                                <q-item-label>Delete Asset</q-item-label>
                            </q-item-section>
                        </q-item>
                    </q-list>
                </q-btn-dropdown>
                <div class="row">
                    <div class="col-5">
                        <q-list>
                            <q-item-label header>General</q-item-label>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Name</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                    <q-item-label caption>{{asset.name}}
                                    </q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Model</q-item-label>
                                </q-item-section>

                                <q-item-section side top>
                                    <q-item-label caption>{{asset.model["name"]}} {{asset.model["number"]}}
                                    </q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Status</q-item-label>
                                </q-item-section>

                                <q-item-section side top>
                                    <q-item-label caption>{{asset.status_label["name"]}}
                                    </q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Company</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                    <q-item-label caption>{{asset.company["name"]}}
                                    </q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Location</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                    <q-item-label caption>Location
                                    </q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Serial</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                    <q-item-label caption>{{asset.serial}}</q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-item-label header>Purchasing</q-item-label>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Manufacturer</q-item-label>
                                </q-item-section>

                                <q-item-section side top>
                                    <q-item-label caption>
                                        manufacturer</q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Purchase Date</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                    <q-item-label caption>
                                        {{asset.purchase_date}}</q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Purchase Cost</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                    <q-item-label caption>
                                        ${{asset.purchase_cost}}
                                    </q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-item-label header>Warranty</q-item-label>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Months</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                    <q-item-label caption>
                                        months</q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Expires</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                    <q-item-label caption>
                                        expires</q-item-label>
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>End of Life</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                    <q-item-label caption>
                                        eol</q-item-label>
                                </q-item-section>
                            </q-item>
                        </q-list>
                    </div>
                    <div class="col-7">
                        <div class="row">
                            <div class="col-12">
                                <q-card class="q-mx-sm q-mb-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-h6">Checked Out To</span>
                                        <div>
                                            {{asset.assigned_to}}
                                        </div>
                                    </q-card-section>
                                </q-card>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-lg-4 col-md-6 col-sm-12 col-xs-12">
                                <q-card class="q-mx-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-weight-light">App
                                            Vulnerabilities</span>
                                        <div class="text-h6">
                                            {{asset.name}}
                                        </div>
                                    </q-card-section>
                                </q-card>
                            </div>
                            <div class="col-lg-4 col-md-6 col-sm-12 col-xs-12">
                                <q-card class="q-mx-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-weight-light">App
                                            Vulnerabilities</span>
                                        <div class="text-h6">
                                            {{asset.name}}
                                        </div>
                                    </q-card-section>
                                </q-card>
                            </div>
                            <div class="col-lg-4 col-md-6 col-sm-12 col-xs-12">
                                <q-card class="q-mx-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-weight-light">Human Risks</span>
                                        <div class="text-h6">
                                            {{asset.name}}
                                        </div>
                                    </q-card-section>
                                </q-card>
                            </div>
                        </div>
                    </div>
                </div>
            </q-tab-panel>

            <q-tab-panel name="licenses">
                Lorem ipsum dolor sit amet consectetur adipisicing elit.
            </q-tab-panel>

            <q-tab-panel name="maintenances">
                Lorem ipsum dolor sit amet consectetur adipisicing elit.
            </q-tab-panel>
        </q-tab-panels>
    </q-card>
</template>

<script>
    import axios from "axios";
    import { ref, computed, watch, onMounted } from "vue";
    import { useQuasar, useDialogPluginComponent, date } from "quasar";
    import { notifySuccess, notifyError, notifyWarning } from "@/utils/notify";
    import { useRouter } from 'vue-router';
    import AddAsset from "@/components/integrations/snipeit/modals/AddAsset";

    export default {
        name: "SnipeIT",
        emits: [...useDialogPluginComponent.emits],
        props: ['agent'],

        setup(props) {
            const { dialogRef, onDialogHide } = useDialogPluginComponent();
            const $q = useQuasar();

            const tab = ref("")
            const asset = ref([])
            const foundAsset = ref(null)

            function getHardware() {
                asset.value = []
                axios
                    .get(`/snipeit/hardware/`, { params: { status: 'All' } })
                    .then(r => {
                        const tacticalAgentModels = []
                        const tacticalAgentHostname = []
                        const snipeITAssetsModelNameNumber = []
                        const snipeITAssetsModelNumber = []
                        const snipeITAssetHostnames = []
                        tacticalAgentModels.push(props.agent.wmi_detail.comp_sys[0][0].Model)
                        tacticalAgentModels.push(props.agent.wmi_detail.comp_sys_prod[0][0].Name)
                        tacticalAgentHostname.push(props.agent.hostname)

                        let i = 0;
                        do {
                            for (let hardwareObj of r.data.rows) {
                                snipeITAssetsModelNameNumber.push(hardwareObj.model.name + " " + hardwareObj.model_number)
                                snipeITAssetsModelNumber.push(hardwareObj.model_number)
                                snipeITAssetHostnames.push(hardwareObj.name)

                                //Match on Model Number
                                const modelNumber = tacticalAgentModels.filter(element => snipeITAssetsModelNumber.includes(element))
                                //Match on Model Name and Number
                                const modelNameNumber = tacticalAgentModels.filter(element => snipeITAssetsModelNameNumber.includes(element))
                                //Match on hostname
                                const hostnameMatch = tacticalAgentHostname.filter(element => snipeITAssetHostnames.includes(element))

                                if (modelNumber.length > 0 && hostnameMatch.length > 0 || modelNameNumber.length > 0 && hostnameMatch.length > 0 || modelNumber.length > 0 && modelNameNumber.length > 0 && hostnameMatch.length > 0) {
                                    asset.value = hardwareObj
                                    tab.value = 'asset'
                                    foundAsset.value = true
                                    return;
                                } else {
                                    foundAsset.value = false
                                }
                            }
                            i++;
                        } while (i < r.data.rows.length);

                        notifyError("Could not find a " + props.agent.hostname + " asset by the same name and model number in Snipe-IT")
                        addAsset()

                    })
                    .catch(e => {
                        console.log(e)
                    });
            }

            function addAsset() {
                $q.dialog({
                    component: AddAsset,
                    componentProps: {
                        agent: props.agent,
                    }
                }).onOk(() => {
                    getHardware()
                })
            }
            onMounted(() => {
                getHardware()
            });

            return {
                tab,
                asset,
                // quasar dialog
                dialogRef,
                onDialogHide,
            };
        },
    };
</script>