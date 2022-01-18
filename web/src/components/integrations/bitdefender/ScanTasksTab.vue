<template>
  <div class="q-pa-md">
    <q-table
      :rows="rows"
      :columns="columns"
      row-key="name"
      :filter="filter"
      :pagination="pagination"
    >
      <template v-slot:top-left>
        <q-btn flat dense @click="getScanTasks()" icon="refresh" />
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
</template>

<script>
import axios from "axios";
// composable imports
import { ref, onMounted } from "vue";
import { useQuasar, useDialogPluginComponent } from "quasar";

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
  name: "ScanTasksTab",
  emits: [...useDialogPluginComponent.emits],
  props: ['endpoint'],

  setup(props) {
    const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
    const $q = useQuasar();
    let rows = ref([])

    function getScanTasks() {
      $q.loading.show()
      axios
        .get(`/bitdefender/tasks/`)
        .then(r => {
          rows.value = []
          for (let item of r.data.result.items) {
            let itemObj = {
              id: item.id,
              name: item.name,
              startDate: item.startDate,
              status: item.status,
            }
            rows.value.push(itemObj)
          }
          $q.loading.hide()
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