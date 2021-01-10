<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card class="q-dialog-plugin" style="min-width: 80vw; min-height: 65vh; overflow-x: hidden">
      <q-bar>
        <q-btn @click="getChartData" class="q-mr-sm" dense flat push icon="refresh" />
        {{ title }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <div class="row">
        <span v-if="!showChart" class="q-pa-md">No Data</span>
        <q-space />
        <q-select
          v-model="timeFilter"
          emit-value
          map-options
          style="width: 200px"
          :options="timeFilterOptions"
          outlined
          dense
          class="q-pr-md q-pt-md"
          @input="getChartData"
        />
      </div>
      <apexchart
        v-if="showChart"
        class="q-pt-md"
        type="line"
        height="70%"
        :options="chartOptions"
        :series="[{ name: 'Percentage', data: history }]"
      />
    </q-card>
  </q-dialog>
</template>
<script>
import VueApexCharts from "vue-apexcharts";

export default {
  name: "CheckGraph",
  components: {
    apexchart: VueApexCharts,
  },
  props: {
    check: !Object,
  },
  data() {
    return {
      history: [],
      timeFilter: 1,
      timeFilterOptions: [
        { value: 1, label: "Last 24 Hours" },
        { value: 7, label: "Last 7 Days" },
        { value: 30, label: "Last 30 Days" },
      ],
      chartOptions: {
        tooltip: {
          x: {
            format: "dd MMM h:mm:sst",
          },
        },
        chart: {
          id: "chart2",
          type: "line",
          toolbar: {
            show: true,
          },
          animations: {
            enabled: false,
          },
        },
        colors: ["#027BE3"],
        stroke: {
          width: 3,
        },
        dataLabels: {
          enabled: false,
        },
        fill: {
          opacity: 1,
        },
        markers: {
          size: 1,
        },
        xaxis: {
          type: "datetime",
          labels: {
            datetimeUTC: false,
          },
        },
        yaxis: {
          min: 0,
          max: 100,
        },
        noData: {
          text: "No Data",
        },
        theme: {
          mode: this.$q.dark.isActive ? "dark" : "light",
        },
      },
    };
  },
  computed: {
    title() {
      return this.check.readable_desc + " history";
    },
    showChart() {
      return !this.$q.loading.isActive && this.history.length > 0;
    },
  },
  methods: {
    getChartData() {
      this.$q.loading.show();

      this.$axios
        .patch(`/checks/history/${this.check.id}/`, { timeFilter: this.timeFilter })
        .then(r => {
          this.history = r.data;
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    show() {
      this.$refs.dialog.show();
    },
    hide() {
      this.$refs.dialog.hide();
    },
    onHide() {
      this.$emit("hide");
    },
  },
  created() {
    this.getChartData();

    // add annotation depending on check type
    if (
      this.check.check_type === "cpuload" ||
      this.check.check_type === "memory" ||
      this.check.check_type === "diskspace"
    ) {
      this.chartOptions["annotations"] = {
        position: "front",
        yaxis: [
          {
            y: this.check.threshold,
            strokeDashArray: 0,
            borderColor: "#C10015",
            width: 3,
            label: {
              borderColor: "#C10015",
              style: {
                color: "#FFF",
                background: "#C10015",
              },
              text: "Threshold",
            },
          },
        ],
      };
    }
  },
};
</script>
