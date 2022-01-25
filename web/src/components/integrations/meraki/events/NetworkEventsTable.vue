<template>
  <q-table
    :rows="rows"
    :columns="columns"
    row-key="occurredAt"
    :pagination="pagination"
    :loading="loading"
    :filter="filter"
    wrap-cells
  >
    <template v-slot:loading v-model="loading">
      <q-inner-loading showing color="primary" />
    </template>
    <template v-slot:top-right="props">
      <q-input outlined clearable dense debounce="300" v-model="filter" label="Search">
        <template v-slot:prepend>
          <q-icon name="search" />
        </template>
      </q-input>
      <q-btn
        flat
        dense
        :icon="props.inFullscreen ? 'fullscreen_exit' : 'fullscreen'"
        @click="props.toggleFullscreen"
        class="q-ml-md"
      />
      <q-btn flat dense color="primary" icon="archive" no-caps @click="exportTable" />
    </template>
    <template v-slot:top-left>
      <q-btn
        flat
        dense
        @click="
  getEvents(networkID);
timespan.label = '';
        "
        icon="refresh"
        label="Network Events"
      />
      <q-btn
        icon="event"
        :label="timespan.label"
        no-caps
        dense
        flat
        color="primary"
        class="q-ml-md"
      >
        <q-popup-proxy @before-show="updateProxy" transition-show="scale" transition-hide="scale">
          <q-date
            subtitle="Ending Before date"
            v-model="selectedDate"
            :navigation-min-year-month="minMonth"
            :navigation-max-year-month="maxMonth"
          >
            <div class="row items-center justify-end q-gutter-sm">
              <q-btn label="Cancel" color="primary" flat v-close-popup />
              <q-btn
                label="OK"
                color="primary"
                flat
                @click="getEvents(networkID, selectedDate)"
                v-close-popup
              />
            </div>
          </q-date>
        </q-popup-proxy>
      </q-btn>
    </template>
    <template v-slot:body="props">
      <q-tr :props="props">
        <q-td key="occurredAt" :props="props">
          <span class="text-caption">{{ props.row.occurredAt }}</span>
        </q-td>
        <q-td key="client" :props="props">
          <span class="text-caption">{{ props.row.client }}</span>
        </q-td>
        <q-td key="description" :props="props">
          <span class="text-caption">{{ props.row.description }}</span>
        </q-td>
        <q-td key="details" :props="props">
          <span class="text-caption">{{ props.row.details }}</span>
        </q-td>
      </q-tr>
    </template>
  </q-table>
</template>

<script>
import axios from "axios";
import { ref, onMounted, onBeforeMount } from "vue";
import { useQuasar, date, exportFile } from "quasar";

const columns = [
  {
    name: "occurredAt",
    required: true,
    label: "Time",
    align: "left",
    field: (row) => row.occurredAt,
    format: (val) => `${val}`,
    sortable: true,
  },
  {
    name: "client",
    align: "left",
    label: "Client",
    field: "client",
    sortable: false,
  },
  {
    name: "description",
    label: "Description",
    field: "description",
    align: "left",
    sortable: false,
  },

  {
    name: "details",
    label: "Details",
    field: "details",
    align: "left",
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

    const rows = ref([])
    const events = ref("")
    const maxMonth = ref("")
    const minMonth = ref("")
    const timespan = ref({ label: "", value: 0 })
    const loading = ref(false)
    const filter = ref("")
    const selectedDate = ref("")
    const updateProxy = ref("")
    const save = ref("")
    const timespanDropdown = ref(false)

    function getEvents(timespan) {
      const currentDate = new Date();
      maxMonth.value = date.formatDate(currentDate, "YYYY/MM");
      const newDate = date.subtractFromDate(currentDate, { month: 2 });
      minMonth.value = date.formatDate(newDate, "YYYY/MM");
      timespanDropdown.value = false;
      let url = null;
      if (typeof timespan === "string" && typeof timespan !== null) {
        const endingBefore = date.formatDate(timespan, "YYYY-MM-DDT00:00:00.000Z");
        const formattedDate = date.formatDate(timespan, "MMM DD, YYYY @ h:mm A");
        timespan.value.label = "Before: " + formattedDate;

        url = "endingBefore=" + endingBefore;
      } else if (typeof timespan === "number" && timespan !== null) {
        url = timespan;
      } else {
        url = 7200;
      }
      axios
        .get(`/meraki/` + props.networkID + `/events/` + url + `/`)
        .then(r => {
          rows.value = [];
          events.value = "";
          events.value = r.data.events;
          for (let event of events.value) {
            let arr = Object.entries(event.eventData);
            let result = arr.join(" ").replaceAll(",", ": ");
            let formattedDate = date.formatDate(
              event.occurredAt,
              "MMM DD, YYYY @ h:mm A"
            );
            let eventObj = {
              occurredAt: formattedDate,
              client: event.clientDescription,
              details: result,
              description: event.description,
            };
            rows.value.push(eventObj);
          }
        })
        .catch(e => {
          console.log(e)
        });
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
    onBeforeMount(() => {
      getEvents()
    })


    return {
      pagination: {
        sortBy: 'time',
        descending: true,
        page: 1,
        rowsPerPage: 10
      },
      events,
      columns,
      rows,
      timespan,
      loading,
      filter,
      selectedDate,
      updateProxy,
      save,
      timespanDropdown,
      minMonth,
      maxMonth,
      exportTable,
    }
  }
}

</script>