<template>
  <div class="q-pa-md">
    <q-table :rows="rows" :columns="columns" row-key="id" :pagination="pagination" :filter="filter"
      :selected-rows-label="getSelected" selection="multiple" v-model:selected="selected">

      <template v-slot:top-left>
        <q-btn @click="getEndpoints()" class="q-mr-sm" dense flat push icon="refresh" />
        <q-btn-dropdown dense flat class="q-mx-md" label="Actions">
          <q-list>
            <q-item clickable v-close-popup @click="getQuickScanConfirmModal()">
              <q-item-section>
                <q-item-label>Quick Scan</q-item-label>
              </q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="getQuarantine()">
              <q-item-section>
                <q-item-label>View Quarantine</q-item-label>
              </q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="getScanTasks()">
              <q-item-section>
                <q-item-label>View Scan Tasks</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-btn-dropdown>
      </template>
      <template v-slot:top-right>
        <q-input outlined v-model="filter" label="Search current page" dense debounce="300" clearable>
          <template v-slot:prepend>
            <q-icon name="search" />
          </template>
        </q-input>
      </template>
      <template v-slot:body="props">
        <q-tr :props="props">
          <q-td>
            <q-checkbox v-model="props.selected" />
          </q-td>
          <q-td key="endpointName" :props="props">
            <span class="text-caption">{{ props.row.name }}</span>
          </q-td>
          <q-td key="ip" :props="props">
            <span class="text-caption">{{ props.row.ip }}</span>
          </q-td>
          <q-td key="managed" :props="props">
            <span class="text-caption">{{ props.row.managed }}</span>
          </q-td>
          <q-td key="os" :props="props">
            <span class="text-caption">{{ props.row.os }}</span>
          </q-td>
          <q-td key="macs" :props="props">
            <span class="text-caption">{{ props.row.macs }}</span>
          </q-td>
        </q-tr>
      </template>
      <template v-slot:bottom>
        <q-space />
        <span>{{totalCount}} total results</span>
        <q-btn icon="first_page" color="grey-8" round dense flat :disable="pageNumber === 1"
          @click="getEndpoints(false, false, true, false)" />
        <q-btn icon="chevron_left" color="grey-8" round dense flat :disable="pageNumber === 1"
          @click="getEndpoints(false, true, false, false)" />
        Page {{pageNumber}} of {{pagesCount}}
        <q-btn icon="chevron_right" color="grey-8" round dense flat :disable="pageNumber === pagesCount"
          @click="getEndpoints(true, false, false, false)" />
        <q-btn icon="last_page" color="grey-8" round dense flat :disable="pageNumber === pagesCount"
          @click="getEndpoints(false, false, false, true)" />
      </template>
    </q-table>
  </div>
</template>

<script>
  import axios from "axios";
  // composable imports
  import { watch, ref, onMounted } from "vue";
  import { useMeta, useQuasar, useDialogPluginComponent } from "quasar";
  import { notifySuccess, notifyWarning, notifyError } from "@/utils/notify";
  import QuarantineView from "@/components/integrations/bitdefender/modals/QuarantineView";
  import QuickScanConfirmModal from "@/components/integrations/bitdefender/modals/QuickScanConfirmModal";
  import ScanTasksView from "@/components/integrations/bitdefender/modals/ScanTasksView";

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
      name: "managed",
      required: true,
      label: "Mangaed",
      align: "left",
      sortable: true,

    },
    {
      name: "os",
      required: true,
      label: "OS",
      align: "left",
      sortable: true,

    },
    {
      name: "macs",
      required: true,
      label: "MACs",
      align: "left",
      sortable: true,

    },
  ]

  export default {
    name: "BitdefenderDashboard",
    emits: [...useDialogPluginComponent.emits],
    components: {},
    setup(props) {
      const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
      const $q = useQuasar();
      const rows = ref([])
      let selected = ref([])
      let totalCount = ref(null)
      let pageNumber = ref(null)
      let pagesCount = ref(null)
      let rowsPerPage = ref(50)

      function getEndpoints(nextPage, prevPage, firstPage, lastPage) {

        if (nextPage) {
          pageNumber.value = pageNumber.value + 1
        } else if (prevPage) {
          pageNumber.value = pageNumber.value - 1
        } else if (firstPage) {
          pageNumber.value = 1
        } else if (lastPage) {
          pageNumber.value = pagesCount.value
        } else { pageNumber.value = 1 }

        useMeta({ title: `Bitdefender GravityZone | Tactical RMM Integration Dashboard` });
        axios
          .get(`/bitdefender/endpoints/` + pageNumber.value)
          .then(r => {
            pageNumber.value = r.data.result.page
            pagesCount.value = r.data.result.pagesCount
            rowsPerPage.value = r.data.result.perPage
            totalCount.value = r.data.result.total
            rows.value = []
            for (let endpoint of r.data.result.items) {
              let endpointObj = {
                id: endpoint.id,
                name: endpoint.name,
                ip: endpoint.details.ip,
                managed: endpoint.details.isManaged,
                os: endpoint.details.operatingSystemVersion,
                macs: endpoint.details.macs.length > 0 ? endpoint.details.macs : ""
              }
              rows.value.push(endpointObj)
            }
          })
          .catch(e => {
            console.log(e)
          });
      }

      function getSelected() {
        return selected.value.length === 0
          ? ""
          : `${selected.value.length} record${selected.value.length > 1 ? "s" : ""
          } selected of ${rows.value.length}`;
      }


      function getQuickScanConfirmModal() {
        if (selected.value.length > 0) {
          $q.dialog({
            component: QuickScanConfirmModal,
            componentProps: { selected: selected.value }
          })
        } else {
          notifyError("Please select an endpoint");
        }
      }

      function getScanTasks() {
        $q.dialog({
          component: ScanTasksView,
          componentProps: { selected: selected.value }
        })
      }

      function getQuarantine() {
          $q.dialog({
            component: QuarantineView,
            componentProps: { selected: selected.value }
          })
      }

      onMounted(() => {
        getEndpoints();
      });

      return {
        pagination: {
          sortBy: 'desc',
          descending: false,
          page: pageNumber.value,
          pages: pagesCount.value,
          rowsPerPage: rowsPerPage.value
        },
        rows,
        columns,
        filter: ref(""),
        selected,
        pageNumber,
        pagesCount,
        totalCount,
        getEndpoints,
        getSelected,
        getScanTasks,
        getQuickScanConfirmModal,
        getQuarantine,
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