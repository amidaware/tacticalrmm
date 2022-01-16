<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide" persistant>
    <q-card class="q-dialog-plugin" style="width: 60vw">
      <q-stepper v-model="step" ref="stepper" color="primary" animated>
        <q-step :name="1" :title="'Add ' + agent.hostname" icon="settings" :done="step > 1">
          <q-form>
            <q-input filled v-model="assetName" label="Name *" dense :rules="[(val) => !!val || '*Required']" />
            <q-select filled dense v-model="assetCompany" label="Company *" :options="companyOptions"
              :rules="[(val) => !!val || '*Required']" />
            <q-select filled dense v-model="assetLocation" label="Location *" :options="locationOptions"
              :rules="[ (val) => !!val || '*Required' ]" />
            <q-select filled v-model="assetTag" label="Asset Tag *" :options="assetTagOptions" dense
              :rules="[(val) => !!val || '*Required']" />
            <q-input filled v-model="assetSerial" label="Serial *" dense :rules="[(val) => !!val || '*Required']" />
            <q-select filled dense v-model="assetStatus" label="Status" :options="assetStatusOptions"
              :rules="[(val) => !!val || '*Required']" />
            <q-input filled dense class="q-mb-md" v-model="assetPurchaseCost" label="Purchase Cost" prefix="$"
              style="width:200px" mask="#.##" fill-mask="0" reverse-fill-mask />
              <q-input dense stack-label label="Purchase Date" filled v-model="assetPurchaseDate" mask="date" :rules="['date']">
                <template v-slot:append>
                  <q-icon name="event" class="cursor-pointer">
                    <q-popup-proxy ref="qDateProxy" cover transition-show="scale" transition-hide="scale">
                      <q-date v-model="assetPurchaseDate">
                        <div class="row items-center justify-end">
                          <q-btn v-close-popup label="Close" color="primary" flat />
                        </div>
                      </q-date>
                    </q-popup-proxy>
                  </q-icon>
                </template>
              </q-input>
            <q-input filled dense class="q-mb-md" v-model="assetWarrantyMonths" label="Warranty (Months)"
              style="width:300px" />
            <q-input filled dense class="q-mb-md" v-model="assetOrderNumber" label="Order Number" style="width:300px" />
          </q-form>
        </q-step>
        <q-step :name="2" title="Choose Asset Model" icon="create_new_folder" :done="step > 2">
          <q-btn :disable="newModelButton" class="q-mb-md" icon="add" label="New Model" @click="addModel()" />
          <q-select filled dense v-model="assetModel" label="Model *" :options="assetModelOptions"
            :rules="[ (val) => !!val || '*Required' ]" />
          <q-select filled v-model="assetManufacturer" label="Manufacturer *" :options="assetManufacturerOptions" dense
            :rules="[(val) => !!val || '*Required']" />
          <q-select filled v-model="assetSupplier" label="Supplier" :options="assetSupplierOptions" dense
            class="q-mb-md" />
          <q-select filled v-model="assetCategory" label="Category *" :options="assetCategoryOptions" dense
            :rules="[(val) => !!val || '*Required']" />
        </q-step>
        <q-step :name="3" title="Review" icon="create_new_folder" :done="step > 3">
          <q-list>
            <q-item dense>
              <q-item-section top>
                <q-item-label>Name</q-item-label>
              </q-item-section>
              <q-item-section side top>
                {{assetName}}
              </q-item-section>
            </q-item>
            <q-item dense>
              <q-item-section top>
                <q-item-label>Asset Tag</q-item-label>
              </q-item-section>
              <q-item-section side top>
                {{assetTag}}
              </q-item-section>
            </q-item>
            <q-item dense>
              <q-item-section top>
                <q-item-label>Model</q-item-label>
              </q-item-section>
              <q-item-section side top>
                {{assetModel.label}}
              </q-item-section>
            </q-item>
            <q-item dense>
              <q-item-section top>
                <q-item-label>Serial</q-item-label>
              </q-item-section>
              <q-item-section side top>
                {{assetSerial}}
              </q-item-section>
            </q-item>
            <q-item dense>
              <q-item-section top>
                <q-item-label>Status</q-item-label>
              </q-item-section>
              <q-item-section side top>
                {{assetStatus.label}}
              </q-item-section>
            </q-item>
            <q-item dense>
              <q-item-section top>
                <q-item-label>Company</q-item-label>
              </q-item-section>
              <q-item-section side top>
                {{assetCompany.label}}
              </q-item-section>
            </q-item>
            <q-item dense>
              <q-item-section top>
                <q-item-label>Location</q-item-label>
              </q-item-section>
              <q-item-section side top>
                {{assetLocation.label}}
              </q-item-section>
            </q-item>
            <q-item dense>
              <q-item-section top>
                <q-item-label>Manufacturer</q-item-label>
              </q-item-section>
              <q-item-section side top>
                {{assetManufacturer.label}}
              </q-item-section>
            </q-item>
            <q-item dense>
              <q-item-section top>
                <q-item-label>Supplier</q-item-label>
              </q-item-section>
              <q-item-section side top>
                {{assetSupplier.label}}
              </q-item-section>
            </q-item>
            <q-item dense>
              <q-item-section top>
                <q-item-label>Category</q-item-label>
              </q-item-section>
              <q-item-section side top>
                {{assetCategory.label}}
              </q-item-section>
            </q-item>
            <q-item dense>
              <q-item-section top>
                <q-item-label>Purchase Cost</q-item-label>
              </q-item-section>
              <q-item-section side top>
                {{assetPurchaseCost}}
              </q-item-section>
            </q-item>
            <q-item dense>
              <q-item-section top>
                <q-item-label>Purchase Date</q-item-label>
              </q-item-section>
              <q-item-section side top>
                {{assetPurchaseDate}}
              </q-item-section>
            </q-item>
            <q-item dense>
              <q-item-section top>
                <q-item-label>Warranty (Months)</q-item-label>
              </q-item-section>
              <q-item-section side top>
                {{assetWarrantyMonths}}
              </q-item-section>
            </q-item>
            <q-item dense>
              <q-item-section top>
                <q-item-label>Order Number</q-item-label>
              </q-item-section>
              <q-item-section side top>
                {{assetOrderNumber}}
              </q-item-section>
            </q-item>
          </q-list>
        </q-step>
        <template v-slot:navigation>
          <q-stepper-navigation align="right">
            <q-btn flat v-if="step > 1" color="primary" @click="$refs.stepper.previous()" label="Back" />
            <q-btn flat v-if="step != 3" @click="$refs.stepper.next()" color="primary" label="Next" />
            <q-btn flat v-else-if="isEditAsset=false" @click="addAsset()" color="primary" label="Add" />
            <q-btn flat v-else @click="editAsset()" color="primary" label="Edit" />
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
  import { useQuasar, useDialogPluginComponent, date } from "quasar";
  import { notifySuccess, notifyError } from "@/utils/notify";

  export default {
    name: "EditAsset",
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
      const assetSupplier = ref("")
      const assetSupplierOptions = ref([])
      const assetCategory = ref("")
      const assetCategoryOptions = ref([])
      const assetPurchaseCost = ref("")
      const assetPurchaseDate = ref("")
      const assetWarrantyMonths = ref("")
      const assetOrderNumber = ref("")
      const addNewModel = ref(false)
      const step = ref(1)
      const newModelButton = ref(true)
      const isEditAsset = ref(true)

      function getAsset() {
        assetName.value = props.asset.name
        assetTagOptions.value.push(props.agent.wmi_detail.comp_sys_prod[0][0].IdentifyingNumber)
        assetTagOptions.value.push(props.agent.wmi_detail.comp_sys_prod[0][0].Name)
        assetSerial.value = props.agent.wmi_detail.os[0][0].SerialNumber
        assetCompany.value = {label:props.asset.company.name, value:props.asset.company.id}
        assetLocation.value = {label:props.asset.location.name, value:props.asset.location.id}
        assetTag.value = props.asset.asset_tag
        assetStatus.value = {label:props.asset.status_label.name, value:props.asset.status_label.id}
        assetPurchaseDate.value = props.asset.purchase_date.date
        assetPurchaseCost.value = props.asset.purchase_cost
        assetCategory.value = {label:props.asset.category.name, value: props.asset.category.id}
        assetSupplier.value = {label:props.asset.supplier.name, value:props.asset.supplier.id}
        assetWarrantyMonths.value = props.asset.warranty_months.split(' ')[0]
        assetOrderNumber.value = props.asset.order_number
        assetManufacturer.value = {label:props.asset.manufacturer.name, value:props.asset.manufacturer.id}
        assetModel.value = {label:props.asset.model.name, value:props.asset.model.id}
      }

      function getCompanies() {
        $q.loading.show()
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
            companyOptions.value.sort((a, b) => (a.label > b.label) ? 1 : -1)
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
            locationOptions.value.sort((a, b) => (a.label > b.label) ? 1 : -1)
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
            assetStatusOptions.value.sort((a, b) => (a.label > b.label) ? 1 : -1)
            $q.loading.hide()
          })
          .catch(e => {
            console.log(e.response.data)
          });
      }

      function getModels() {
        $q.loading.show()
        axios
          .get(`/snipeit/models/`)
          .then(r => {
            assetModelOptions.value = []
            for (let model of r.data.rows) {
              let modelObj = {
                label: model.name + ' / ' + model.category.name + ' (' + model.model_number + ')',
                value: model.id,
              }
              assetModelOptions.value.push(modelObj)
            }
            assetModelOptions.value.sort((a, b) => (a.label > b.label) ? 1 : -1)
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
            assetCategoryOptions.value.sort((a, b) => (a.label > b.label) ? 1 : -1)

            $q.loading.hide()
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
            assetManufacturerOptions.value.sort((a, b) => (a.label > b.label) ? 1 : -1)
          })
          .catch(e => {
            console.log(e.response.data)
          });
      }

      function getSuppliers() {
        $q.loading.show()
        axios
          .get(`/snipeit/suppliers/`)
          .then(r => {
            for (let supplier of r.data.rows) {
              let supplierObj = {
                label: supplier.name,
                value: supplier.id,
              }
              assetSupplierOptions.value.push(supplierObj)
              assetSupplierOptions.value.sort((a, b) => (a.label > b.label) ? 1 : -1)
            }
            $q.loading.hide()
          })
          .catch(e => {
            console.log(e)
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
          let modelObj = {
            label: val['assetModel'],
            value: val['assetModelID'],
          }
          assetModelOptions.value.push(modelObj)
          assetModel.value = modelObj
        })
      }

      function editAsset() {
        $q.loading.show()
        let data = {
          asset_tag: assetTag.value,
          status_id: assetStatus.value.value,
          model_id: assetModel.value.value,
          name: assetName.value,
          serial: assetSerial.value,
          rtd_location_id: assetLocation.value.value,
          company_id: assetCompany.value.value,
          manufacturer_id: assetManufacturer.value.value,
          supplier_id: assetSupplier.value ? assetSupplier.value.value : null,
          purchase_cost: assetPurchaseCost.value ? assetPurchaseCost.value : null,
          purchase_date: assetPurchaseDate.value ? date.formatDate(assetPurchaseDate.value, 'YYYY-MM-DD') : null,
          warranty_months: assetWarrantyMonths.value ? assetWarrantyMonths.value : null,
          order_number: assetOrderNumber.value ? assetOrderNumber.value : null
        }
        if (assetTag.value && assetStatus.value && assetModel.value && assetName.value && assetSerial.value && assetLocation.value && assetCompany.value) {
          axios
            .put(`/snipeit/hardware/` + props.asset.id + `/`, data)
            .then(r => {
              if (r.data.status === 'error') {
                notifyError(r.data.messages)
              } else {
                notifySuccess(r.data.messages)
                onDialogOK()
              }
              $q.loading.hide()
            })
            .catch(e => {
              console.log(e.reponse.data)
            });
        } else {
          notifyError("Please make sure all fields are filled in")
          $q.loading.hide()
        }
      }

      onMounted(() => {
        getAsset()
        getCompanies()
        getLocations()
        getAssetStatus()
      });

      watch(step, (selection) => {
        if (selection === 2) {
          getModels()
          getSuppliers()
          getManufacturers()
          getCategories()
        }
      })

      watch([assetManufacturer, assetCategory], ([manufacturer, category]) => {
        if (manufacturer && category) {
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
        assetSupplier,
        assetSupplierOptions,
        assetCategory,
        assetCategoryOptions,
        assetPurchaseCost,
        assetPurchaseDate,
        assetWarrantyMonths,
        assetOrderNumber,
        editAsset,
        addModel,
        // quasar dialog plugin
        dialogRef,
        onDialogHide,
      }
    }
  }
</script>