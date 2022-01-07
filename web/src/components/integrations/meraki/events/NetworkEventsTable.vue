<template>
<<<<<<< HEAD
  <div class="q-pb-md q-pl-md q-gutter-sm">
    <q-breadcrumbs>
      <q-breadcrumbs-el icon="home" class="text-black" />
      <q-breadcrumbs-el class="text-black" :label="organizationName" />
      <q-breadcrumbs-el class="text-black" :label="networkName" />
      <q-breadcrumbs-el class="text-black" label="Events" />
    </q-breadcrumbs>
  </div>
=======
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
  <q-table :rows="rows" :columns="columns" row-key="occurredAt" v-model:pagination="pagination" :loading="loading"
    :filter="filter" wrap-cells>
    <template v-slot:loading v-model="loading">
      <q-inner-loading showing color="primary" />
    </template>
    <template v-slot:top-right="props">
      <q-input outlined clearable dense debounce="300" v-model="filter" label="Search">
        <template v-slot:prepend>
          <q-icon name="search" />
        </template>
      </q-input>
      <q-btn flat dense :icon="props.inFullscreen ? 'fullscreen_exit' : 'fullscreen'" @click="props.toggleFullscreen"
        class="q-ml-md" />
      <q-btn flat dense color="primary" icon="archive" no-caps @click="exportTable" />
    </template>
    <template v-slot:top-left>
      <q-btn flat dense @click="
            getEvents(networkID);
            timespan.label = '';
          " icon="refresh" />
      <q-btn icon="event" :label="timespan.label" no-caps dense flat color="primary" class="q-ml-md">
        <q-popup-proxy @before-show="updateProxy" transition-show="scale" transition-hide="scale">
          <q-date subtitle="Ending Before date" v-model="selectedDate" :navigation-min-year-month="minMonth"
            :navigation-max-year-month="maxMonth">
            <div class="row items-center justify-end q-gutter-sm">
              <q-btn label="Cancel" color="primary" flat v-close-popup />
              <q-btn label="OK" color="primary" flat @click="getEvents(networkID, selectedDate)" v-close-popup />
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
  import { ref } from "vue";
  import { date } from "quasar";
  import { exportFile, useQuasar } from "quasar";

  import axios from "axios";

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
    /**
     * Excel accepts \n and \r in strings, but some other CSV parsers do not
     * Uncomment the next two lines to escape new lines
     */
    // .split('\n').join('\\n')
    // .split('\r').join('\\r')

    return `"${formatted}"`;
  }

  export default {
    name: "NetworkEventsTable",
    props: ["organizationID", "organizationName", "networkID", "networkName"],
    data() {
      return {
        pagination: {
          rowsPerPage: 10,
          sortBy: "time",
          descending: true,
        },
        events: "",
        columns,
        rows: [],
        timespan: { label: "", value: 0 },
        loading: ref(false),

        filter: ref(""),
        selectedDate: "",
        updateProxy: "",
        save: "",
        timespanDropdown: false,
        minMonth: "",
        maxMonth: "",
      };
    },
    methods: {
      getEvents: function getEvents(networkID, timespan) {
        const currentDate = new Date();
        this.maxMonth = date.formatDate(currentDate, "YYYY/MM");
        const newDate = date.subtractFromDate(currentDate, { month: 2 });
        this.minMonth = date.formatDate(newDate, "YYYY/MM");
        this.timespanDropdown = false;
        let url = null;
        if (typeof timespan === "string" && typeof timespan !== null) {
          const endingBefore = date.formatDate(timespan, "YYYY-MM-DDT00:00:00.000Z");
          const formattedDate = date.formatDate(timespan, "MMM DD, YYYY HH:MM aa");
          this.timespan.label = "Before: " + formattedDate;

          url = "endingBefore=" + endingBefore;
        } else if (typeof timespan === "number" && timespan !== null) {
          url = timespan;
        } else {
          url = 7200;
        }
        this.loading = true;
        axios
          .get(`/meraki/` + this.networkID + `/events/` + url + `/`)
          .then(r => {
            this.rows = [];
            this.events = "";
            this.events = r.data.events;
            for (let event of this.events) {
              let arr = Object.entries(event.eventData);
              let result = arr.join(" ").replaceAll(",", ": ");
              let formattedDate = date.formatDate(
                event.occurredAt,
                "MMM DD, YYYY h:mm:ss aa"
              );
              let eventObj = {
                occurredAt: formattedDate,
                client: event.clientDescription,
                details: result,
                description: event.description,
              };
              this.rows.push(eventObj);
            }
            this.loading = false;
          })
          .catch(e => {

          });
      },
      exportTable() {
        // naive encoding to csv format
        const content = [this.columns.map((col) => wrapCsvValue(col.label))]
          .concat(
            this.rows.map((row) =>
              this.columns
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
      },
    },
    mounted() {
      this.getEvents();
    },
  };
</script>