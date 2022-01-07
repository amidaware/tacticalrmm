<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide" persistant>
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-bar>
        Add Asset
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-stepper v-model="step" ref="stepper" color="primary" animated>
        <q-step :name="1" :title="'Add ' + agent.hostname" icon="settings" :done="step > 1">
          <q-form>
            <q-input filled v-model="assetName" label="Name" dense :rules="[(val) => !!val || '*Required']" />
            <q-select filled dense v-model="assetCompany" label="Company" :options="companyOptions"
              :rules="[(val) => !!val || '*Required']" />
            <q-select filled dense v-model="assetLocation" label="Location" :options="locationOptions"
              :rules="[ (val) => !!val || '*Required' ]" />
            <q-select filled v-model="assetTag" label="Asset Tag" :options="assetTagOptions" dense
              :rules="[(val) => !!val || '*Required']" />
            <q-input filled v-model="assetSerial" label="Serial" dense :rules="[(val) => !!val || '*Required']" />
            <q-select filled dense v-model="assetStatus" label="Status" :options="assetStatusOptions"
              :rules="[(val) => !!val || '*Required']" />
          </q-form>
        </q-step>

        <q-step :name="2" title="Associate" icon="create_new_folder" :done="step > 2">
          <q-btn :disable="newModelButton" class="q-mb-md" icon="add" label="New Model" @click="addModel()" />
          <q-select filled dense v-model="assetModel" label="Model" :options="assetModelOptions"
            :rules="[ (val) => !!val || '*Required' ]" />
          <q-select filled v-model="assetManufacturer" label="Manufacturer" :options="assetManufacturerOptions" dense
              :rules="[(val) => !!val || '*Required']" />
          <q-select filled v-model="assetCategory" label="Category" :options="assetCategoryOptions" dense
              :rules="[(val) => !!val || '*Required']" />
        </q-step>

        <q-step :name="3" title="Confirm" icon="create_new_folder" :done="step > 3">
          <q-list dense>
            <q-item>
              <q-item-section>
                clearTreeSelected
              </q-item-section>
            </q-item>
            <q-item>
              <q-item-section>
                clearTreeSelected
              </q-item-section>
            </q-item>
            <q-item>
              <q-item-section>
                clearTreeSelected
              </q-item-section>
            </q-item>
            <q-item>
              <q-item-section>
                clearTreeSelected
              </q-item-section>
            </q-item>
            <q-item>
              <q-item-section>
                clearTreeSelected
              </q-item-section>
            </q-item>
          </q-list>
        </q-step>

        <template v-slot:navigation>
          <q-stepper-navigation>
            <q-btn v-if="step != 3" @click="$refs.stepper.next()" color="primary" label="Continue" />
            <q-btn v-else @click="addAsset()" color="primary" label="Finish" />
            <q-btn v-if="step > 1" flat color="primary" @click="$refs.stepper.previous()" label="Back"
              class="q-ml-sm" />
          </q-stepper-navigation>
        </template>
      </q-stepper>
    </q-card>
  </q-dialog>
</template>

<script>
  import axios from "axios";
  // composable imports
  import { ref, computed, onMounted, watch } from "vue";
  import { useQuasar, useDialogPluginComponent } from "quasar";
  import { notifySuccess, notifyError } from "@/utils/notify";
  import AddModel from "@/components/integrations/snipeit/modals/AddModel";

  export default {
    name: "AddAsset",
    emits: [...useDialogPluginComponent.emits],
    props: ['agent', 'asset'],

    setup(props) {
      const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
      const $q = useQuasar();
      const assetName = ref("")
      const companyOptions = ref([])
      const assetCompany = ref("")
      const assetLocation = ref("")
      const locationOptions = ref([])
      const assetTag = ref("")
      const assetTagOptions = ref([])
      const assetSerial = ref("")
      const assetStatus = ref("")
      const assetStatusOptions = ref([])
      const assetModel = ref("")
      const assetModelOptions = ref([])
      const assetManufacturer = ref("")
      const assetManufacturerOptions = ref([])
      const assetCategory = ref("")
      const assetCategoryOptions = ref([])
      const addNewModel = ref(false)
      const step = ref(1)
      const newModelButton = ref(true)

      function getTacticalAgent() {
        assetName.value = props.agent.hostname
        assetTagOptions.value.push(props.agent.wmi_detail.comp_sys_prod[0][0].IdentifyingNumber)
        assetTagOptions.value.push(props.agent.wmi_detail.comp_sys_prod[0][0].Name)
        assetSerial.value = props.agent.wmi_detail.os[0][0].SerialNumber
      }

      function getCompanies() {
        axios
          .get(`/snipeit/companies/`)
          .then(r => {
            companyOptions.value = []
            for (let company of r.data.rows) {
              let companyObj = {
                label: company.name,
                value: company.id
              }
              companyOptions.value.push(companyObj)
            }
          })
          .catch(e => {
            console.log(e.response.data)
          });
      }

      function getLocations() {
        axios
          .get(`/snipeit/locations/`)
          .then(r => {
            locationOptions.value = []
            for (let location of r.data.rows) {
              let locationObj = {
                label: location.name,
                value: location.id
              }
              locationOptions.value.push(locationObj)
            }
          })
          .catch(e => {
            console.log(e.response.data)
          });
      }

      function getAssetStatus() {
        axios
          .get(`/snipeit/statuslabels/`)
          .then(r => {
            assetStatusOptions.value = []
            for (let status of r.data.rows) {
              let statusObj = {
                label: status.name,
                value: status.id,
              }
              assetStatusOptions.value.push(statusObj)
            }
          })
          .catch(e => {
            console.log(e.response.data)
          });
      }

      function getModels() {
        axios
          .get(`/snipeit/models/`)
          .then(r => {
            assetModelOptions.value = []
            for (let model of r.data.rows) {
              let modelObj = {
                label: model.name + " " + model.model_number,
                value: model.id,
              }
              assetModelOptions.value.push(modelObj)
            }
          })
          .catch(e => {
            console.log(e.response.data)
          });
      }

      function getCategories() {
          axios
          .get(`/snipeit/categories/`)
          .then(r => {
              assetCategoryOptions.value = []
              for (let category of r.data.rows) {
              let assetCategoryObj = {
                  label: category.name,
                  value: category.id,
              }
              assetCategoryOptions.value.push(assetCategoryObj)
              }
          })
          .catch(e => {
              console.log(e.response.data)
          });
      }

      function getManufacturers() {
        axios
        .get(`/snipeit/manufacturers/`)
        .then(r => {
            assetManufacturerOptions.value = []
            for (let manufacturer of r.data.rows) {
            let assetManufacturerObj = {
                label: manufacturer.name,
                value: manufacturer.id,
            }
            assetManufacturerOptions.value.push(assetManufacturerObj)
            }
        })
        .catch(e => {
            console.log(e.response.data)
        });
    }

      function addModel() {
        $q.dialog({
          component: AddModel,
          componentProps: {
            agent: props.agent,
            manufacturer: assetManufacturer.value,
            category: assetCategory.value
          }
         }).onOk(val => {
           console.log(val)
              let modelObj = {
                label: val['assetModel'],
                value: val['assetModelID'],
              }
              assetModelOptions.value.push(modelObj)
              assetModel.value = modelObj
        })
      }

      function addAsset(){
        let data = {
          asset_tag: assetTag.value,
          status_id: assetStatus.value.value,
          model_id: assetModel.value.value,
          name: assetName.value,
          serial: assetSerial.value,
          location_id: assetLocation.value.value,
          company_id: assetCompany.value.value
        }

        axios
        .post(`/snipeit/hardware/`, data)
        .then(r => {
          if (r.data.status === 'error'){
            notifyError("The Asset Tag must be unique to Snipe-IT")
          }else{
            notifySuccess(props.agent.hostname + " has been added as an asset to Snipe-IT")
            onDialogOK()
          }
        })
        .catch(e => {
          console.log(e)
        });
      }

      onMounted(() => {
        getTacticalAgent()
        getCompanies()
        getLocations()
        getAssetStatus()
      });

      watch(step, (selection) => {
        if (selection === 2) {
          getModels()
          getManufacturers()
          getCategories()
        }
      })

      watch([assetManufacturer, assetCategory], ([manufacturer, category]) => {
        console.log(manufacturer, category)
        if(manufacturer && category){
          console.log()
          newModelButton.value = false
        }
      })

      return {
        step,
        newModelButton,
        assetName,
        assetCompany,
        companyOptions,
        assetLocation,
        locationOptions,
        assetTag,
        assetTagOptions,
        assetSerial,
        assetStatus,
        assetStatusOptions,
        assetModel,
        assetModelOptions,
        assetManufacturer,
        assetManufacturerOptions,
        assetCategory,
        assetCategoryOptions,
        addAsset,
        addModel,
        // quasar dialog plugin
        dialogRef,
        onDialogHide,
      }
    }
  }
</script>