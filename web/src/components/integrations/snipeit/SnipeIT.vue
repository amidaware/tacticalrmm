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
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
                        <q-item clickable v-close-popup @click="scanEndpointConfirm('quick')">
=======
                        <q-item clickable v-close-popup @click="checkout()" v-if="asset.user_can_checkout">
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                        <q-item clickable v-close-popup @click="checkout()">
>>>>>>> checkin/checkout and delete asset
=======
                        <q-item clickable v-close-popup @click="checkout()" v-if="asset.user_can_checkout">
>>>>>>> display depreciation values
                            <q-item-section>
                                <q-item-label>Checkout</q-item-label>
                            </q-item-section>
                        </q-item>

<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
                        <q-item clickable v-close-popup @click="scanEndpointConfirm('full')">
=======
                        <q-item clickable v-close-popup @click="checkin()" v-else>
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                        <q-item clickable v-close-popup @click="checkin()">
>>>>>>> checkin/checkout and delete asset
=======
                        <q-item clickable v-close-popup @click="checkin()" v-else>
>>>>>>> display depreciation values
                            <q-item-section>
                                <q-item-label>Checkin</q-item-label>
                            </q-item-section>
                        </q-item>

<<<<<<< HEAD
<<<<<<< HEAD
                        <q-item clickable v-close-popup @click="scanEndpointConfirm('full')">
=======
                        <q-item clickable v-close-popup @click="deleteAsset()">
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                        <q-item clickable v-close-popup @click="deleteAsset()">
>>>>>>> checkin/checkout and delete asset
                            <q-item-section>
                                <q-item-label>Delete Asset</q-item-label>
                            </q-item-section>
                        </q-item>
                    </q-list>
                </q-btn-dropdown>
                <div class="row">
                    <div class="col-5">
                        <q-list>
<<<<<<< HEAD
<<<<<<< HEAD
                            <q-item-label header>General</q-item-label>
=======
                        <q-item-section>
                            <q-item-label header>GENERAL </q-item-label>
                        </q-item-section>
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                        <q-item-section>
                            <q-item-label header>GENERAL </q-item-label>
                        </q-item-section>
>>>>>>> more reorganization of unused files/folders and list formatting
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Name</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
<<<<<<< HEAD
<<<<<<< HEAD
                                    <q-item-label caption>{{asset.name}}
                                    </q-item-label>
=======
                                    {{asset.name}}
                                    
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                                    {{asset.name}}
                                    
>>>>>>> more reorganization of unused files/folders and list formatting
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
<<<<<<< HEAD
<<<<<<< HEAD
                                    <q-item-label>Model</q-item-label>
=======
                                    <q-item-label>Model Name</q-item-label>
>>>>>>> more reorganization of unused files/folders and list formatting
                                </q-item-section>

                                <q-item-section side top>
                                    {{asset.model.name}}
                                    
                                </q-item-section>
                            </q-item>
                           <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Model Number</q-item-label>
                                </q-item-section>

                                <q-item-section side top>
                                    {{asset.model_number}}
                                    
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Serial</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
<<<<<<< HEAD
<<<<<<< HEAD
                                    <q-item-label caption>{{asset.status_label["name"]}}
                                    </q-item-label>
=======
                                    <q-item-label>Model Name</q-item-label>
                                </q-item-section>

                                <q-item-section side top>
                                    {{asset.model.name}}
                                    
                                </q-item-section>
                            </q-item>
                           <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Model Number</q-item-label>
                                </q-item-section>

                                <q-item-section side top>
                                    {{asset.model_number}}
                                    
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                                    <q-item-label caption>{{asset.serial}}</q-item-label>
>>>>>>> checkin/checkout and delete asset
=======
                                    {{asset.serial}}
>>>>>>> more reorganization of unused files/folders and list formatting
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
<<<<<<< HEAD
<<<<<<< HEAD
                                    <q-item-label>Company</q-item-label>
=======
                                    <q-item-label>Status</q-item-label>
>>>>>>> checkin/checkout and delete asset
                                </q-item-section>

                                <q-item-section side top>
<<<<<<< HEAD
                                    <q-item-label caption>{{asset.status_label.name}}
                                    </q-item-label>
=======
                                    <q-item-label>Serial</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                    {{asset.serial}}
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                                    {{asset.status_label.name}}
                                    
>>>>>>> more reorganization of unused files/folders and list formatting
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
<<<<<<< HEAD
<<<<<<< HEAD
                                    <q-item-label>Location</q-item-label>
=======
                                    <q-item-label>Company</q-item-label>
>>>>>>> checkin/checkout and delete asset
                                </q-item-section>
                                <q-item-section side top>
<<<<<<< HEAD
                                    <q-item-label caption>{{asset.company.name}}
                                    </q-item-label>
=======
                                    <q-item-label>Status</q-item-label>
                                </q-item-section>

                                <q-item-section side top>
                                    {{asset.status_label.name}}
                                    
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                                    {{asset.company.name}}
                                    
>>>>>>> more reorganization of unused files/folders and list formatting
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
<<<<<<< HEAD
<<<<<<< HEAD
                                    <q-item-label>Serial</q-item-label>
=======
                                    <q-item-label>Location</q-item-label>
>>>>>>> checkin/checkout and delete asset
                                </q-item-section>
                                <q-item-section side top v-if="asset.location">
                                    {{asset.location.name}}
                                    
                                </q-item-section>
                            </q-item>
<<<<<<< HEAD

                            <q-item-label header>Purchasing</q-item-label>
=======
                                    <q-item-label>Company</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
                                    {{asset.company.name}}
                                    
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Location</q-item-label>
                                </q-item-section>
                                <q-item-section side top v-if="asset.location">
                                    {{asset.location.name}}
                                    
                                </q-item-section>
                            </q-item>
                            <q-separator inset/>
<<<<<<< HEAD
                            <q-item-label header>PURCHASING</q-item-label>
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
<q-separator inset/>
=======
>>>>>>> implement q.loading and bitdefender component work
                            <q-item-label header>PURCHASING</q-item-label>
>>>>>>> more reorganization of unused files/folders and list formatting
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Manufacturer</q-item-label>
                                </q-item-section>

                                <q-item-section side top>
<<<<<<< HEAD
<<<<<<< HEAD
                                    <q-item-label caption>
<<<<<<< HEAD
                                        manufacturer</q-item-label>
=======
                                    
                                        {{asset.manufacturer.name}}
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                                        {{asset.manufacturer.name}}</q-item-label>
>>>>>>> checkin/checkout and delete asset
=======
                                    
                                        {{asset.manufacturer.name}}
>>>>>>> more reorganization of unused files/folders and list formatting
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Purchase Date</q-item-label>
                                </q-item-section>
<<<<<<< HEAD
<<<<<<< HEAD
                                <q-item-section side top>
<<<<<<< HEAD
                                    <q-item-label caption>
                                        {{asset.purchase_date}}</q-item-label>
=======
                                <q-item-section side top v-if="asset.purchase_date">
           
                                        {{asset.purchase_date.formatted}}
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                                    <q-item-label caption v-if="asset.purchase_date">
                                        {{asset.purchase_date.formatted}}</q-item-label>
>>>>>>> display depreciation values
=======
                                <q-item-section side top v-if="asset.purchase_date">
           
                                        {{asset.purchase_date.formatted}}
>>>>>>> more reorganization of unused files/folders and list formatting
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Purchase Cost</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
<<<<<<< HEAD
<<<<<<< HEAD
                                    <q-item-label caption>
=======
                                    
>>>>>>> more reorganization of unused files/folders and list formatting
                                        ${{asset.purchase_cost}}
                                    
                                </q-item-section>
                            </q-item>
<<<<<<< HEAD
                            <q-item-label header>Warranty</q-item-label>
=======
                                    
                                        ${{asset.purchase_cost}}
                                    
                                </q-item-section>
                            </q-item>
                            <q-separator inset/>
                            <q-item-label header>WARRANTY</q-item-label>
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                            <q-separator inset/>
                            <q-item-label header>WARRANTY</q-item-label>
>>>>>>> more reorganization of unused files/folders and list formatting
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Months</q-item-label>
                                </q-item-section>
                                <q-item-section side top>
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
                                    <q-item-label caption>
<<<<<<< HEAD
                                        months</q-item-label>
=======
                                    
                                        {{asset.warranty_months}}
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                                        {{asset.warranty_months}}</q-item-label>
>>>>>>> checkin/checkout and delete asset
=======
                                    <q-item-label caption v-if="asset.warranty_months">
                                        {{asset.warranty_months.formatted}}</q-item-label>
>>>>>>> display depreciation values
=======
                                    
                                        {{asset.warranty_months}}
>>>>>>> more reorganization of unused files/folders and list formatting
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>Expires</q-item-label>
                                </q-item-section>
<<<<<<< HEAD
<<<<<<< HEAD
                                <q-item-section side top>
<<<<<<< HEAD
                                    <q-item-label caption>
<<<<<<< HEAD
                                        expires</q-item-label>
=======
                                <q-item-section side top v-if="asset.warranty_expires">
                                    
                                        {{asset.warranty_expires.formatted}}
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                                        {{asset.warranty_expires}}</q-item-label>
>>>>>>> checkin/checkout and delete asset
=======
                                    <q-item-label caption v-if="asset.warranty_expires">
                                        {{asset.warranty_expires.formatted}}</q-item-label>
>>>>>>> display depreciation values
=======
                                <q-item-section side top v-if="asset.warranty_expires">
                                    
                                        {{asset.warranty_expires.formatted}}
>>>>>>> more reorganization of unused files/folders and list formatting
                                </q-item-section>
                            </q-item>
                            <q-item dense>
                                <q-item-section top>
                                    <q-item-label>End of Life</q-item-label>
                                </q-item-section>
<<<<<<< HEAD
<<<<<<< HEAD
                                <q-item-section side top>
<<<<<<< HEAD
                                    <q-item-label caption>
<<<<<<< HEAD
                                        eol</q-item-label>
=======
                                <q-item-section side top v-if="asset.eol">
                                   
                                        {{asset.eol.formatted}}
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                                        {{asset.eol}}</q-item-label>
>>>>>>> checkin/checkout and delete asset
=======
                                    <q-item-label caption v-if="asset.eol">
                                        {{asset.eol.formatted}}</q-item-label>
>>>>>>> display depreciation values
=======
                                <q-item-section side top v-if="asset.eol">
                                   
                                        {{asset.eol.formatted}}
>>>>>>> more reorganization of unused files/folders and list formatting
                                </q-item-section>
                            </q-item>
                        </q-list>
                    </div>
                    <div class="col-7">
<<<<<<< HEAD
<<<<<<< HEAD
                        <div class="row">
=======
                        <div class="row q-mt-sm">
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                        <div class="row q-mt-sm">
>>>>>>> more reorganization of unused files/folders and list formatting
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
<<<<<<< HEAD
                                <q-card class="q-mx-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-weight-light">Current Value</span>
                                        <div class="text-h6">
<<<<<<< HEAD
                                            {{asset.name}}
=======
                                <q-card class="q-mx-sm q-my-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-weight-light">Current Value</span>
                                        <div class="text-h6">
                                            ${{currentValue}}
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                                            ${{currentValue}}
>>>>>>> display depreciation values
                                        </div>
                                    </q-card-section>
                                </q-card>
                            </div>
                            <div class="col-lg-4 col-md-6 col-sm-12 col-xs-12">
<<<<<<< HEAD
<<<<<<< HEAD
                                <q-card class="q-mx-sm">
=======
                                  <q-card class="q-mx-sm">
>>>>>>> display depreciation values
                                    <q-card-section class="text-center">
                                        <span class="text-weight-light">Monthly Depcreciation</span>
                                        <div class="text-h6">
<<<<<<< HEAD
                                            {{asset.name}}
=======
                                  <q-card class="q-mx-sm q-my-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-weight-light">Monthly Depcreciation</span>
                                        <div class="text-h6">
                                            ${{monthlyDepreciation}}
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                                            ${{monthlyDepreciation}}
>>>>>>> display depreciation values
                                        </div>
                                    </q-card-section>
                                </q-card>
                            </div>
                            <div class="col-lg-4 col-md-6 col-sm-12 col-xs-12">
<<<<<<< HEAD
                                <q-card class="q-mx-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-weight-light">Difference</span>
                                        <div class="text-h6">
<<<<<<< HEAD
                                            {{asset.name}}
=======
                                <q-card class="q-mx-sm q-my-sm">
                                    <q-card-section class="text-center">
                                        <span class="text-weight-light">Difference</span>
                                        <div class="text-h6">
                                            ${{difference}}
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                                            ${{difference}}
>>>>>>> display depreciation values
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
<<<<<<< HEAD
<<<<<<< HEAD
=======
    import Checkout from "@/components/integrations/snipeit/modals/Checkout";
    import Checkin from "@/components/integrations/snipeit/modals/Checkin";
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
    import Checkout from "@/components/integrations/snipeit/modals/Checkout";
    import Checkin from "@/components/integrations/snipeit/modals/Checkin";
>>>>>>> checkin/checkout and delete asset

    export default {
        name: "SnipeIT",
        emits: [...useDialogPluginComponent.emits],
        props: ['agent'],

        setup(props) {
<<<<<<< HEAD
<<<<<<< HEAD
            const { dialogRef, onDialogHide } = useDialogPluginComponent();
=======
            const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
            const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();
>>>>>>> checkin/checkout and delete asset
            const $q = useQuasar();

            const tab = ref("")
            const asset = ref([])
            const foundAsset = ref(null)
<<<<<<< HEAD
<<<<<<< HEAD

            function getHardware() {
<<<<<<< HEAD
                asset.value = []
=======
            const monthlyDepreciation = ref("")
            const currentValue = ref("")
            const difference = ref("")
<<<<<<< HEAD

=======
            const monthlyDepreciation = ref("")
            const currentValue = ref("")
            const difference = ref("")
>>>>>>> display depreciation values
            function getHardware() {
                $q.loading.show()
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======

>>>>>>> checkin/checkout and delete asset
=======

            function getHardware() {
                $q.loading.show()
>>>>>>> implement q.loading and bitdefender component work
                axios
                    .get(`/snipeit/hardware/`, { params: { status: 'All' } })
                    .then(r => {
                        const tacticalAgentModels = []
                        const tacticalAgentHostname = []
                        const snipeITAssetsModelNameNumber = []
                        const snipeITAssetsModelNumber = []
<<<<<<< HEAD
<<<<<<< HEAD
=======
                        const snipeITAssetTags = []
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                        const snipeITAssetTags = []
>>>>>>> checkin/checkout and delete asset
                        const snipeITAssetHostnames = []
                        tacticalAgentModels.push(props.agent.wmi_detail.comp_sys[0][0].Model)
                        tacticalAgentModels.push(props.agent.wmi_detail.comp_sys_prod[0][0].Name)
                        tacticalAgentHostname.push(props.agent.hostname)

                        let i = 0;
                        do {
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
                            for (let hardwareObj of r.data.rows) {
                                snipeITAssetsModelNameNumber.push(hardwareObj.model.name + " " + hardwareObj.model_number)
                                snipeITAssetsModelNumber.push(hardwareObj.model_number)
                                snipeITAssetHostnames.push(hardwareObj.name)
=======
=======
                            // for (let hardwareObj of r.data.rows) {
>>>>>>> checkin/checkout and delete asset
=======
>>>>>>> implement q.loading and bitdefender component work
                                snipeITAssetsModelNameNumber.push(r.data.rows[i].model.name + " " + r.data.rows[i].model_number)
                                snipeITAssetsModelNumber.push(r.data.rows[i].model_number)
                                snipeITAssetTags.push(r.data.rows[i].asset_tag)
                                snipeITAssetHostnames.push(r.data.rows[i].name)
<<<<<<< HEAD
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
>>>>>>> checkin/checkout and delete asset

                                //Match on Model Number
                                const modelNumber = tacticalAgentModels.filter(element => snipeITAssetsModelNumber.includes(element))
                                //Match on Model Name and Number
                                const modelNameNumber = tacticalAgentModels.filter(element => snipeITAssetsModelNameNumber.includes(element))
<<<<<<< HEAD
<<<<<<< HEAD
=======
                                //Match on Asset Tag
                                const assetTag = tacticalAgentModels.filter(element => snipeITAssetTags.includes(element))
>>>>>>> checkin/checkout and delete asset
                                //Match on hostname
                                const hostnameMatch = tacticalAgentHostname.filter(element => snipeITAssetHostnames.includes(element))

                                if (modelNumber.length > 0 && hostnameMatch.length > 0 || modelNameNumber.length > 0 && hostnameMatch.length > 0 || modelNumber.length > 0 && modelNameNumber.length > 0 && hostnameMatch.length > 0 || assetTag.length > 0 && hostnameMatch.length > 0) {
                                    asset.value = []
                                    asset.value = r.data.rows[i]
                                    tab.value = 'asset'
                                    foundAsset.value = true
=======
                                //Match on Asset Tag
                                const assetTag = tacticalAgentModels.filter(element => snipeITAssetTags.includes(element))
                                //Match on hostname
                                const hostnameMatch = tacticalAgentHostname.filter(element => snipeITAssetHostnames.includes(element))

                                if (modelNumber.length > 0 && hostnameMatch.length > 0 || modelNameNumber.length > 0 && hostnameMatch.length > 0 || modelNumber.length > 0 && modelNameNumber.length > 0 && hostnameMatch.length > 0 || assetTag.length > 0 && hostnameMatch.length > 0) {
                                    if (r.data.rows[i].eol && r.data.rows[i].purchase_date){
                                        const newDate = new Date()
                                        const eolDate = r.data.rows[i].eol.date
                                        const purchase_date = r.data.rows[i].purchase_date.date
                                        const unit = 'months'

                                        const depreciationDateDiff = date.getDateDiff(eolDate, purchase_date, unit)
                                        const depreciationCost = parseInt(r.data.rows[i].purchase_cost.replace(/,/g, ''), 10) / depreciationDateDiff
                                        const currentDepreciationValue = date.getDateDiff(newDate, purchase_date, unit)

                                        currentValue.value = (parseInt(r.data.rows[i].purchase_cost.replace(/,/g, ''), 10) - (currentDepreciationValue * depreciationCost)).toFixed(2)
                                        difference.value = (currentDepreciationValue * depreciationCost).toFixed(2)
                                        monthlyDepreciation.value = depreciationCost.toFixed(2)
                                    }
                                    asset.value = []
                                    asset.value = r.data.rows[i]
                                    tab.value = 'asset'
                                    foundAsset.value = true
                                    $q.loading.hide()
<<<<<<< HEAD
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
>>>>>>> implement q.loading and bitdefender component work
                                    return;
                                } else {
                                    foundAsset.value = false
                                }
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
                            }
=======
                            // }

>>>>>>> checkin/checkout and delete asset
                            i++;
                        } while (i < r.data.rows.length);

=======
                            i++;
                        } while (i < r.data.rows.length);
                        $q.loading.hide()
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                            i++;
                        } while (i < r.data.rows.length);
                        $q.loading.hide()
>>>>>>> implement q.loading and bitdefender component work
                        notifyError("Could not find a " + props.agent.hostname + " asset by the same name and model number in Snipe-IT")
                        addAsset()

                    })
                    .catch(e => {
                        console.log(e)
<<<<<<< HEAD
<<<<<<< HEAD
                    });
=======
                });
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                });
>>>>>>> implement q.loading and bitdefender component work
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
<<<<<<< HEAD
<<<<<<< HEAD
=======
=======
>>>>>>> checkin/checkout and delete asset

            function checkout(){
                $q.dialog({
                    component: Checkout,
                    componentProps: {
                        agent: props.agent,
                        asset: asset.value
                    }
                }).onOk(() => {
                    getHardware()
                })
            }

            function checkin(){
                $q.dialog({
                    component: Checkin,
                    componentProps: {
                        agent: props.agent,
                        asset: asset.value
                    }
                }).onOk(() => {
                    getHardware()
                })
            }

            function deleteAsset(){
                axios
                .delete(`/snipeit/hardware/` + asset.value.id + `/`)
                .then(r => {
                    if (r.data.status === 'error'){
                        notifyError(r.data.messages)
                    }else{
                        notifySuccess(props.agent.hostname + " has been deleted from Snipe-IT")
                    }
                })
                .catch(e => {
                    console.log(e)
                });
            }

<<<<<<< HEAD
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
>>>>>>> checkin/checkout and delete asset
            onMounted(() => {
                getHardware()
            });

            return {
                tab,
                asset,
<<<<<<< HEAD
<<<<<<< HEAD
=======
                checkout,
                checkin,
                deleteAsset,
                monthlyDepreciation,
                currentValue,
                difference,
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
                checkout,
                checkin,
                deleteAsset,
<<<<<<< HEAD
>>>>>>> checkin/checkout and delete asset
=======
                monthlyDepreciation,
                currentValue,
                difference,
>>>>>>> display depreciation values
                // quasar dialog
                dialogRef,
                onDialogHide,
            };
        },
    };
</script>