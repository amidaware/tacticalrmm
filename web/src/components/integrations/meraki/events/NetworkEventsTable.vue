<template>
  <q-card>
    <q-table
      class="q-mt-sm"
      :rows="rows"
      :columns="columns"
      row-key="occurredAt"
      :pagination="pagination"
      :loading="tableLoading"
      :filter="filter"
    >
      <template v-slot:top-left>
        <q-btn
          flat
          dense
          @click="selectedDate = ''; timespan.label = ''; timespan.value = 0; getEvents()"
          icon="refresh"
          label="Network Events"
        />
        <q-btn
          icon="event"
          no-caps
          dense
          flat
          color="primary"
          class="q-ml-md"
          :label="timespan.label"
        >
          <q-popup-proxy @before-show="updateProxy" transition-show="scale" transition-hide="scale">
            <q-date v-model="selectedDate" :options="dateOptions">
              <div class="row items-center justify-end q-gutter-sm">
                <q-btn label="Cancel" color="primary" flat v-close-popup />
                <q-btn label="OK" color="primary" flat @click="getEvents()" v-close-popup />
              </div>
            </q-date>
          </q-popup-proxy>
        </q-btn>
      </template>
      <template v-slot:top-right>
        <div>
          <q-input outlined clearable dense debounce="300" v-model="filter" label="Search">
            <template v-slot:prepend>
              <q-icon name="search" />
            </template>
          </q-input>
        </div>
      </template>
      <template v-slot:body="props">
        <q-tr :props="props">
          <q-td key="time" :props="props">{{ props.row.time }}</q-td>
          <q-td key="id" :props="props">
            <q-btn
              flat
              no-caps
              class="text-weight-bold q-px-none"
              @click="getDevicePolicy(props.row)"
            >{{ props.row.id }}</q-btn>
          </q-td>
          <q-td key="mac" :props="props">{{ props.row.mac }}</q-td>
          <q-td key="description" :props="props">{{ props.row.description }}</q-td>
          <q-td key="deviceName" :props="props">{{ props.row.deviceName }}</q-td>
          <q-td key="type" :props="props">{{ props.row.type }}</q-td>
          <q-td key="details" :props="props">{{ props.row.details }}</q-td>
        </q-tr>
      </template>
    </q-table>
  </q-card>
</template>

<script>
import axios from "axios";
import { ref, onMounted } from "vue";
import { useQuasar, date, exportFile } from "quasar";
import Policy from "@/components/integrations/meraki/modals/Policy";

const columns = [
  {
    name: "time",
    required: true,
    label: "Time",
    align: "left",
    field: (row) => row.time,
    format: (val) => `${val}`,
    sortable: true,
  },
  {
    name: "id",
    align: "left",
    label: "Client ID",
    field: "id",
    field: (row) => row.clientId,
    format: (val) => `${val}`,
    sortable: true,
  },
  {
    name: "mac",
    align: "left",
    label: "MAC",
    field: "mac",
    field: (row) => row.clientDescription,
    format: (val) => `${val}`,
    sortable: true,
  },
  {
    name: "description",
    label: "Description",
    field: "description",
    align: "left",
    field: (row) => row.description,
    format: (val) => `${val}`,
    sortable: true,
  },
  {
    name: "deviceName",
    label: "Device Name",
    field: "deviceName",
    align: "left",
    field: (row) => row.deviceName,
    format: (val) => `${val}`,
    sortable: true,
  },
  {
    name: "type",
    label: "Type",
    field: "type",
    align: "left",
    field: (row) => row.type,
    format: (val) => `${val}`,
    sortable: true,
  },
  {
    name: "details",
    label: "Details",
    field: "details",
    align: "left",
    field: (row) => row.details,
    format: (val) => `${val}`,
    sortable: false,
  },
];

function wrapCsvValue(val, formatFn) {
  let formatted = formatFn !== void 0 ? formatFn(val) : val;
  formatted = formatted === void 0 || formatted === null ? "" : String(formatted);
  formatted = formatted.split('"').join('""');

  return `"${formatted}"`;
}

export default {
  name: "NetworkEventsTable",
  props: ["organizationID", "organizationName", "networkID", "networkName"],

  setup(props) {
    const $q = useQuasar();

    const tableLoading = ref(false)
    const rows = ref([])
    const timespan = ref({ label: "", value: 0 })
    const dateOptions = ref([])
    const selectedDate = ref("")
    const updateProxy = ref("")
    const filter = ref("")



    function getDateOptions() {
      for (let i = 0; i < 93; i++) {
        let newDate = date.subtractFromDate(new Date(), { days: i });
        let formattedDate = date.formatDate(newDate, 'YYYY/MM/DD');
        dateOptions.value.push(formattedDate);
      }
    }

    function getEvents() {
      if (selectedDate.value) {
        const startingAfter = date.formatDate(selectedDate.value, 'YYYY-MM-DDT00:00:00.000Z');
        timespan.value.value = "startingAfter=" + startingAfter
        timespan.value.label = "Starting after " + date.formatDate(startingAfter, 'MMM D, YYYY @ hh:mm A')
      }

      axios
        .get(`/meraki/` + props.networkID + `/events/` + timespan.value.value)
        .then(r => {
          console.log(r.data)
          rows.value = []
          for (let event of r.data.events) {
            let eventObj = {
              time: date.formatDate(event.occurredAt, "MMM DD, YYYY @ h:mm A"),
              occurredAt: event.occurredAt,
              id: event.clientId ? event.clientId : "",
              mac: event.clientDescription ? event.clientDescription : "",
              description: event.description,
              deviceName: event.deviceName,
              type: event.type,
              details: Object.entries(event.eventData).join(" ").replaceAll(",", ": ")
            }
            rows.value.push(eventObj)
          }

        })
        .catch(e => {
          console.log(e)
        });
    }

    function getDevicePolicy(client) {
      $q.dialog({
        component: Policy,
        componentProps: {
          networkId: props.networkID,
          client: client
        }
      })
    }

    function exportTable() {
      const content = [columns.map((col) => wrapCsvValue(col.label))]
        .concat(
          rows.value.map((row) =>
            columns
              .map((col) =>
                wrapCsvValue(
                  typeof col.field === "function"
                    ? col.field(row)
                    : row[col.field === void 0 ? col.name : col.field],
                  col.format
                )
              )
              .join(",")
          )
        )
        .join("\r\n");

      const status = exportFile("table-export.csv", content, "text/csv");

      if (status !== true) {
        $q.notify({
          message: "Browser denied file download...",
          color: "negative",
          icon: "warning",
        });
      }
    }

    onMounted(() => {
      getDateOptions()
      getEvents()
    })


    return {
      pagination: {
        sortBy: 'occurredAt',
        descending: true,
        page: 1,
        rowsPerPage: 10
      },
      tableLoading,
      rows,
      columns,
      timespan,
      dateOptions,
      selectedDate,
      updateProxy,
      filter,
      getEvents,
      getDevicePolicy,
      exportTable,
    }
  }
}

</script>