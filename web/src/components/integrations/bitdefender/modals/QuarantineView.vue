<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-layout view="hHh Lpr lff" container class="shadow-2 rounded-borders q-dialog-plugin"
      style="width: 90vw; max-width: 90vw">
      <q-header class="bg-grey-3 text-black">
        <q-bar>
          <q-btn ref="refresh" @click="getQuarantine()" class="q-mr-sm" dense flat push icon="refresh" />Company Quarantine
          <q-space />
          <q-btn dense flat icon="close" v-close-popup>
            <q-tooltip class="bg-white text-primary">Close</q-tooltip>
          </q-btn>
        </q-bar>
      </q-header>
      <q-page-container class="bg-white">
        <q-page>
          <div class="q-pa-md">
            <q-table :rows="rows" :columns="columns" row-key="name" :filter="filter"
              :pagination="pagination">
              <template v-slot:top-right>
                <q-input outlined v-model="filter" label="Search" dense debounce="300" clearable>
                  <template v-slot:prepend>
                    <q-icon name="search" />
                  </template>
                </q-input>
              </template>
                <template v-slot:body="props">
                    <q-tr :props="props">
                    <q-td key="endpointName" :props="props">
                        <span class="text-caption">{{ props.row.name }}</span>
                    </q-td>
                    <q-td key="ip" :props="props">
                        <span class="text-caption">{{ props.row.ip }}</span>
                    </q-td>
                    <q-td key="threatName" :props="props">
                        <span class="text-caption">{{ props.row.threatName }}</span>
                    </q-td>
                    <q-td key="quarantinedOn" :props="props">
                        <span class="text-caption">{{ props.row.quarantinedOn }}</span>
                    </q-td>
                    <q-td key="canBeRemoved" :props="props">
                        <span class="text-caption">{{ props.row.canBeRemoved }}</span>
                    </q-td>
                    <q-td key="canBeRestored" :props="props">
                        <span class="text-caption">{{ props.row.canBeRestored }}</span>
                    </q-td>
                    <q-td key="details" :props="props">
                        <span class="text-caption">{{ props.row.details }}</span>
                    </q-td>
                    </q-tr>
                </template>
            </q-table>
          </div>
        </q-page>
      </q-page-container>
    </q-layout>
  </q-dialog>
</template>

<script>
  import axios from "axios";
  // composable imports
  import { ref, computed, onMounted } from "vue";
  import { useQuasar, useDialogPluginComponent } from "quasar";
  import { notifySuccess, notifyError } from "@/utils/notify";

 const columns = [
    {
      name: "endpointName",
      required: true,
      label: "Endpoint Name",
      align: "left",
      sortable: true,
      field: row => row.name,
      format: val => `${val}`,
    },
    {
      name: "ip",
      required: true,
      label: "IP",
      align: "left",
      sortable: true,

    },
    {
      name: "threatName",
      required: true,
      label: "Threat Name",
      align: "left",
      sortable: true,

    },

    {
      name: "quarantinedOn",
      required: true,
      label: "Quarantined On",
      align: "left",
      sortable: true,

    },
    {
      name: "canBeRemoved",
      required: true,
      label: "Can Be Removed",
      align: "left",
      sortable: true,

    },
    {
      name: "canBeRestored",
      required: true,
      label: "Can Be Restored",
      align: "left",
      sortable: true,

    },
    {
      name: "details",
      required: true,
      label: "Details",
      align: "left",
      sortable: true,

    }
  ]

  export default {
    name: "QuarantineView",
    emits: [...useDialogPluginComponent.emits],
    props: ['selected'],

    setup(props) {
      const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
      const $q = useQuasar();
      let rows = ref([])
      let endpointID = ref("")
      let endpointName = ref("")
    // console.log(props.selected)

        function getQuarantine(){
            for (let endpoint of props.selected){
                endpointID.value = endpoint.id
            }

            axios
            .get(`/bitdefender/quarantine/`)
            .then(r => {
              rows.value = []
                for(let item of r.data.result.items){
                    let itemObj = {
                        id: item.id,
                        name: item.endpointName,
                        ip: item.endpointIP,
                        threatName: item.threatName,
                        quarantinedOn: item.quarantinedOn,
                        canBeRemoved: item.canBeRemoved,
                        canBeRestored: item.canBeRestored,
                        details: item.details.filePath
                    }
                     rows.value.push(itemObj)
                }
            })
            .catch(e => {
                console.log(e)
            });
        }

      onMounted(() => {
        getQuarantine()
      });

      return {
        pagination: {
          sortBy: 'desc',
          descending: false,
          page: 1,
          rowsPerPage: 100
        },
        rows,
        columns,
        filter: ref(""),
        endpointName,
        getQuarantine,
        // quasar dialog plugin
        dialogRef,
        onDialogHide,
      };
    },
  };

</script>