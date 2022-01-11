<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-layout view="hHh Lpr lff" container class="shadow-2 rounded-borders q-dialog-plugin"
      style="width: 90vw; max-width: 90vw">
      <q-header class="bg-grey-3 text-black">
        <q-bar>
          <q-btn ref="refresh" @click="getScanTasks()" class="q-mr-sm" dense flat push icon="refresh" />All Scan Tasks
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
                    <q-td key="name" :props="props">
                        <span class="text-caption">{{ props.row.name }}</span>
                    </q-td>
                    <q-td key="startDate" :props="props">
                        <span class="text-caption">{{ props.row.startDate }}</span>
                    </q-td>
                    <q-td key="status" :props="props">
                        <span class="text-caption" v-if="props.row.status === 1">
                          <q-chip color="primary" dense outline>Pending</q-chip>
                        </span>
                        <span class="text-caption" v-if="props.row.status === 2">
                          <q-chip color="warning" dense outline>In Progress</q-chip>
                        </span>
                        <span class="text-caption" v-if="props.row.status === 3">
                          <q-chip color="positive" text-color="white" outline dense>Finished</q-chip>
                        </span>
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
      name: "name",
      required: true,
      label: "Task Name",
      align: "left",
      sortable: true,
      field: row => row.name,
      format: val => `${val}`,
    },
    {
      name: "startDate",
      required: true,
      label: "Start Date",
      align: "left",
      sortable: true,
      field: row => row.startDate,
      format: val => `${val}`,
    },
    {
      name: "status",
      required: true,
      label: "Status",
      align: "left",
      sortable: true,

    },
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

        function getScanTasks(){
            for (let endpoint of props.selected){
                endpointID.value = endpoint.id
            }

            axios
            .get(`/bitdefender/tasks/`)
            .then(r => {
              rows.value = []
                for(let item of r.data.result.items){
                    let itemObj = {
                        id: item.id,
                        name: item.name,
                        startDate: item.startDate,
                        status: item.status,

                    }
                     rows.value.push(itemObj)
                }

            })
            .catch(e => {
                console.log(e.response.data)
            });
        }

      onMounted(() => {
        getScanTasks()
      });

      return {
        pagination: {
          sortBy: 'startDate',
          descending: true,
          page: 1,
          rowsPerPage: 100
        },
        rows,
        columns,
        filter: ref(""),
        getScanTasks,
        // quasar dialog plugin
        dialogRef,
        onDialogHide,
      };
    },
  };

</script>