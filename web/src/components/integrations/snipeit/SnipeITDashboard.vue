<template>
  <q-layout class="shadow-2 rounded-borders">
    <q-drawer v-model="drawer" show-if-above :mini="!drawer || miniState" @click="drawerClick = !drawerclick" :width="200"
      :breakpoint="100" bordered class="bg-grey-3">
      <q-scroll-area class="fit">
        <q-list>
          <q-item clickable>
            <q-item-section side>
              <q-icon name="devices" />
            </q-item-section>
            <q-item-section>Assets</q-item-section>
            <q-item-section side>
              <q-icon name="keyboard_arrow_right" />
            </q-item-section>
            <q-menu fit square anchor="top right" self="top left">
              <q-item clickable v-close-popup @click="status = 'All';getHardware()">
                List All
              </q-item>
              <q-item clickable v-close-popup @click="status = 'Deployed';getHardware()">
                Deployed
              </q-item>
              <q-item clickable v-close-popup @click="status = 'Ready to Deploy';getHardware()">
                Ready to Deploy
              </q-item>
              <q-item clickable v-close-popup @click="status = 'Pending';getHardware()">
                Pending
              </q-item>
              <q-item clickable v-close-popup @click="status = 'Not Deployable';getHardware()">
                Not Deployable
              </q-item>
              <q-item clickable v-close-popup @click="status = 'Archived';getHardware()">
                Archived
              </q-item>
              <q-item clickable v-close-popup @click="status = 'Requestable';getHardware()">
                Requestable
              </q-item>
            </q-menu>
          </q-item>
        </q-list>
        <q-list>
          <q-item clickable @click="getCompanies()">
            <q-item-section side>
              <q-icon name="business" />
            </q-item-section>
            <q-item-section>Companies</q-item-section>
          </q-item>
          <q-item clickable @click="getLocations()">
            <q-item-section side>
              <q-icon name="travel_explore" />
            </q-item-section>
            <q-item-section>Locations</q-item-section>
          </q-item>
          <q-item clickable @click="getUsers()">
            <q-item-section side>
              <q-icon name="people" />
            </q-item-section>
            <q-item-section>Users</q-item-section>
          </q-item>
        </q-list>
      </q-scroll-area>
    </q-drawer>

    <q-page-container>
      <q-page>
        <q-table :rows="rows" :columns="columns" row-key="id" :pagination="pagination" :filter="filter" flat>
          <template v-slot:top-left>
            <q-btn flat @click="miniState = !miniState" dense icon="menu" class="q-mr-md" />
            <q-btn @click="getHardware()" class="q-mr-sm" dense flat push icon="refresh" />
          </template>
          <template v-slot:top-right>
            <q-input outlined v-model="filter" label="Search" dense debounce="300" clearable>
              <template v-slot:prepend>
                <q-icon name="search" />
              </template>
            </q-input>
          </template>
          <template v-slot:body="props">
            <q-tr :props="props">
              <q-td key="assetName" :props="props">
                <span class="text-caption">{{ props.row.name }}</span>
              </q-td>
              <q-td key="assetTag" :props="props">
                <span class="text-caption">{{ props.row.asset_tag }}</span>
              </q-td>
              <q-td key="model" :props="props">
                <span class="text-caption">{{ props.row.model.name }}</span>
              </q-td>
              <q-td key="category" :props="props">
                <span class="text-caption">{{ props.row.category.name}}</span>
              </q-td>
              <q-td key="status" :props="props">
                <span class="text-caption">{{ props.row.status_label.name}} <q-badge align="middle" color="grey">
                    {{props.row.status_label.status_meta}}</q-badge></span>
              </q-td>
              <q-td key="assignedTo" :props="props">
                <span class="text-caption" v-if="props.row.assigned_to">{{ props.row.assigned_to.name}}</span>
              </q-td>
              <q-td key="location" :props="props">
                <span class="text-caption" v-if="props.row.location">{{ props.row.location.name}}</span>
              </q-td>
              <q-td key="actions" :props="props">
                <q-btn disable padding="xs" size="sm" color="info" icon="content_copy">
                  <q-tooltip class="bg-white text-primary">Copy Asset</q-tooltip>
                </q-btn>
                <q-btn @click="editAssetModal(props.row.id)" class="q-mx-sm" padding="xs" size="sm" color="warning"
                  icon="edit">
                  <q-tooltip class="bg-white text-primary">Edit Asset</q-tooltip>
                </q-btn>
                <q-btn @click="deleteAssetModal(props.row.id)" padding="xs" size="sm" color="negative" icon="delete">
                  <q-tooltip class="bg-white text-primary">Delete Asset</q-tooltip>
                </q-btn>
              </q-td>
            </q-tr>
          </template>
        </q-table>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script>
  import axios from "axios";
  // composable imports
  import { ref, computed, onMounted } from "vue";
  import { useMeta, useQuasar, useDialogPluginComponent } from "quasar";
  import { notifySuccess, notifyError } from "@/utils/notify";
  import AssetEditModal from "@/components/integrations/snipeit/modals/AssetEditModal";
  import AssetDeleteModal from "@/components/integrations/snipeit/modals/AssetDeleteModal";
  import CompaniesModal from "@/components/integrations/snipeit/modals/CompaniesModal";
  import LocationsModal from "@/components/integrations/snipeit/modals/LocationsModal";
  import UsersModal from "@/components/integrations/snipeit/modals/UsersModal";


  const columns = [
    {
      name: "assetName",
      required: true,
      label: "Asset Name",
      align: "left",
      sortable: true,
      field: row => row.name,
      format: val => `${val}`,
    },
    {
      name: "assetTag",
      align: "left",
      label: "Asset Tag",
      field: "assetTag",
      field: row => row.asset_tag,
      sortable: true,
    },
    {
      name: "model",
      align: "left",
      label: "Model",
      field: "model",
      field: row => row.model.name,
      sortable: true,
    },
    {
      name: "category",
      align: "left",
      label: "Category",
      field: "category",
      field: row => row.category.name,
      sortable: true,
    },
    {
      name: "status",
      align: "left",
      label: "Status",
      field: "status",
      sortable: true,
    },
    {
      name: "assignedTo",
      align: "left",
      label: "Checked Out To",
      field: "assignedTo",
      field: row => row.assignedTo,
      sortable: true,
    },
    {
      name: "location",
      align: "left",
      label: "Location",
      field: "location",
      field: row => row.location,
      sortable: true,
    },
    {
      name: "actions",
      align: "left",
      label: "Actions",
      field: "actions",
    },
  ]

  export default {
    name: "SnipeITDashboard",
    emits: [...useDialogPluginComponent.emits],
    components: {},
    setup(props) {
      const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
      const $q = useQuasar();
      const rows = ref([])
      const miniState = ref(false)
      let status = ref('all')

      function getHardware() {
        useMeta({ title: `Snipe-IT | Tactical RMM Integration Dashboard` });

        axios
          .get(`/snipeit/hardware/`, {
                params: {
                    status: status.value,
                }
            })
          .then(r => {
            console.log(r.data)
            rows.value = []
            for (let hardware of r.data.rows) {
              rows.value.push(hardware)
            }
          })
          .catch(e => {
            console.log(e.response.data)
          });
      }

      function getCompanies() {
        $q.dialog({
          component: CompaniesModal,
          componentProps: { }
        })
      }

      function getLocations() {
        $q.dialog({
          component: LocationsModal,
          componentProps: { }
        })
      }

      function getUsers() {
        $q.dialog({
          component: UsersModal,
          componentProps: { }
        })
      }

      function editAssetModal(assetID) {
        $q.dialog({
          component: AssetEditModal,
          componentProps: { assetID: assetID }
        })
          .onOk(() => {
            getHardware()
          })
      }

      function deleteAssetModal(assetID) {
        $q.dialog({
          component: AssetDeleteModal,
          componentProps: { assetID: assetID }
        })
          .onOk(() => {
            getHardware()
          })
      }

      function drawerClick (e) {
          if (miniState.value) {
            miniState.value = false

            e.stopPropagation()
          }
      }
      onMounted(() => {
        getHardware();
      });

      return {
        pagination: {
          sortBy: 'desc',
          descending: false,
          page: 1,
          rowsPerPage: 50
        },
        rows,
        columns,
        filter: ref(""),
        drawer: ref(false),
        miniState,
        drawerClick,
        status,
        getHardware,
        getCompanies,
        getLocations,
        getUsers,
        editAssetModal,
        deleteAssetModal,
        // quasar dialog plugin
        dialogRef,
        onDialogHide,
      };
    },
  };
</script>

<style>
  body {
    overflow: scroll;
  }
</style>