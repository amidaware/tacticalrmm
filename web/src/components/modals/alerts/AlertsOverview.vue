<template>
  <q-dialog ref="dialog" @hide="onHide" maximized transition-show="slide-up" transition-hide="slide-down">
    <q-card>
      <q-bar>
        <q-btn @click="search" class="q-mr-sm" dense flat push icon="refresh" />
        <q-space />
        Alerts Overview
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>

      <div class="text-h6 q-pl-sm q-pt-sm">Filter</div>
      <div class="row">
        <div class="q-pa-sm col-3">
          <q-select
            v-model="clientFilter"
            :options="clientsOptions"
            label="Clients"
            multiple
            outlined
            dense
            use-chips
            map-options
            emit-value
          />
        </div>
        <div class="q-pa-sm col-3">
          <q-select
            v-model="severityFilter"
            :options="severityOptions"
            label="Severity"
            multiple
            outlined
            dense
            use-chips
            map-options
            emit-value
          />
        </div>
        <div class="q-pa-sm col-2">
          <q-select outlined dense v-model="timeFilter" label="Time" emit-value map-options :options="timeOptions" />
        </div>
        <div class="q-pa-sm col-2">
          <q-checkbox outlined dense v-model="includeSnoozed" label="Include snoozed" />
          <q-checkbox outlined dense v-model="includeResolved" label="Include resolved" />
        </div>
        <div class="q-pa-sm col-2">
          <q-btn color="primary" label="Search" @click="search" />
        </div>
      </div>

      <q-separator />

      <q-card-section>
        <q-table
          :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
          class="tabs-tbl-sticky"
          :data="alerts"
          :columns="columns"
          :rows-per-page-options="[0]"
          :pagination.sync="pagination"
          :no-data-label="noDataText"
          :visible-columns="visibleColumns"
          :selected.sync="selectedAlerts"
          selection="multiple"
          binary-state-sort
          row-key="id"
          dense
          virtual-scroll
        >
          <template v-slot:top>
            <div class="col-1 q-table__title">Alerts</div>

            <q-btn-dropdown flat label="Bulk Actions" :disable="selectedAlerts.length === 0 || includeResolved">
              <q-list dense>
                <q-item clickable v-close-popup @click="snoozeAlertBulk(selectedAlerts)">
                  <q-item-section avatar>
                    <q-icon name="alarm_off" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label>Snooze alerts</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item clickable v-close-popup @click="resolveAlertBulk(selectedAlerts)">
                  <q-item-section avatar>
                    <q-icon name="flag" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label>Resolve alerts</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-btn-dropdown>
          </template>

          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <div v-if="!props.row.resolved">
                <q-icon
                  v-if="!props.row.snoozed"
                  name="snooze"
                  size="sm"
                  class="cursor-pointer"
                  @click="snoozeAlert(props.row)"
                >
                  <q-tooltip>Snooze alert</q-tooltip>
                </q-icon>
                <q-icon v-else name="alarm_off" size="sm" class="cursor-pointer" @click="unsnoozeAlert(props.row)">
                  <q-tooltip>Unsnooze alert</q-tooltip>
                </q-icon>
                <q-icon name="flag" size="sm" class="cursor-pointer" @click="resolveAlert(props.row)">
                  <q-tooltip>Resolve alert</q-tooltip>
                </q-icon>
              </div>
            </q-td>
          </template>

          <template v-slot:body-cell-severity="props">
            <q-td :props="props">
              <q-badge :color="alertColor(props.row.severity)">{{ capitalize(props.row.severity) }}</q-badge>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "AlertsOverview",
  mixins: [mixins],
  data() {
    return {
      alerts: [],
      selectedAlerts: [],
      severityFilter: [],
      clientFilter: [],
      timeFilter: 30,
      includeResolved: false,
      includeSnoozed: false,
      searched: false,
      clientsOptions: [],
      severityOptions: [
        { label: "Informational", value: "info" },
        { label: "Warning", value: "warning" },
        { label: "Error", value: "error" },
      ],
      timeOptions: [
        { value: 1, label: "1 Day Ago" },
        { value: 7, label: "1 Week Ago" },
        { value: 30, label: "30 Days Ago" },
        { value: 90, label: "3 Months Ago" },
        { value: 180, label: "6 Months Ago" },
        { value: 365, label: "1 Year Ago" },
        { value: 0, label: "Everything" },
      ],
      columns: [
        {
          name: "alert_time",
          label: "Time",
          field: "alert_time",
          align: "left",
          sortable: true,
          format: a => this.formatDate(a),
        },
        { name: "hostname", label: "Agent", field: "hostname", align: "left", sortable: true },
        {
          name: "alert_type",
          label: "Type",
          field: "alert_type",
          align: "left",
          sortable: true,
          format: a => this.capitalize(a, true),
        },
        { name: "severity", label: "Severity", field: "severity", align: "left", sortable: true },
        { name: "message", label: "Message", field: "message", align: "left", sortable: true },
        {
          name: "resolved_on",
          label: "Resolved On",
          field: "resolved_on",
          align: "left",
          sortable: true,
          format: a => this.formatDate(a, true),
        },
        {
          name: "snooze_until",
          label: "Snoozed Until",
          field: "snooze_until",
          align: "left",
          sortable: true,
          format: a => this.formatDate(a, true),
        },
        { name: "actions", label: "Actions", align: "left" },
      ],
      pagination: {
        rowsPerPage: 0,
        sortBy: "alert_time",
        descending: true,
      },
    };
  },
  computed: {
    noDataText() {
      return this.searched ? "No data found. Try to refine you search" : "Click search to find alerts";
    },
    visibleColumns() {
      return this.columns.map(column => {
        if (column.name === "snooze_until") {
          if (this.includeSnoozed) return column.name;
        } else if (column.name === "resolved_on") {
          if (this.includeResolved) return column.name;
        } else {
          return column.name;
        }
      });
    },
  },
  methods: {
    getClients() {
      this.$axios.get("/clients/clients/").then(r => {
        this.clientsOptions = Object.freeze(r.data.map(client => ({ label: client.name, value: client.id })));
      });
    },
    search() {
      this.$q.loading.show();

      this.selectedAlerts = [];
      this.searched = true;

      let data = {
        snoozedFilter: this.includeSnoozed,
        resolvedFilter: this.includeResolved,
      };

      if (this.clientFilter.length > 0) data["clientFilter"] = this.clientFilter;
      if (this.timeFilter) data["timeFilter"] = this.timeFilter;
      if (this.severityFilter.length > 0) data["severityFilter"] = this.severityFilter;

      this.$axios
        .patch("/alerts/alerts/", data)
        .then(r => {
          this.$q.loading.hide();
          this.alerts = Object.freeze(r.data);
        })
        .catch(e => {
          this.notifyError("There was an issue getting alerts");
          this.$q.loading.hide();
        });
    },
    snoozeAlert(alert) {
      this.$q
        .dialog({
          title: "Snooze Alert",
          message: "How many days to snooze alert?",
          prompt: {
            model: "",
            type: "number",
            isValid: val => !!val && val > 0 && val < 9999,
          },
          cancel: true,
        })
        .onOk(days => {
          this.$q.loading.show();

          const data = {
            id: alert.id,
            type: "snooze",
            snooze_days: days,
          };

          this.$axios
            .put(`alerts/alerts/${alert.id}/`, data)
            .then(r => {
              this.search();
              this.$q.loading.hide();
              this.notifySuccess(`The alert has been snoozed for ${days} days`);
            })
            .catch(e => {
              this.$q.loading.hide();
              this.notifyError("There was an issue snoozing alert");
            });
        });
    },
    unsnoozeAlert(alert) {
      this.$q.loading.show();

      const data = {
        id: alert.id,
        type: "unsnooze",
      };

      this.$axios
        .put(`alerts/alerts/${alert.id}/`, data)
        .then(r => {
          this.search();
          this.$q.loading.hide();
          this.notifySuccess(`The alert has been unsnoozed`);
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError("There was an issue unsnoozing the alert");
        });
    },
    resolveAlert(alert) {
      this.$q.loading.show();

      const data = {
        id: alert.id,
        type: "resolve",
      };

      this.$axios
        .put(`alerts/alerts/${alert.id}/`, data)
        .then(r => {
          this.search();
          this.$q.loading.hide();
          this.notifySuccess("The alert has been resolved");
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError("There was an issue resolving alert");
        });
    },
    resolveAlertBulk(alerts) {
      this.$q.loading.show();

      const data = {
        alerts: alerts.map(alert => alert.id),
        bulk_action: "resolve",
      };

      this.$axios
        .post("alerts/bulk/", data)
        .then(r => {
          this.search();
          this.$q.loading.hide();
          this.notifySuccess("Alerts were resolved");
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError("There was an error resolving alerts");
        });
    },
    snoozeAlertBulk(alerts) {
      this.$q
        .dialog({
          title: "Snooze Alert",
          message: "How many days to snooze alert?",
          prompt: {
            model: "",
            type: "number",
            isValid: val => !!val && val > 0 && val < 9999,
          },
          cancel: true,
        })
        .onOk(days => {
          this.$q.loading.show();

          const data = {
            alerts: alerts.map(alert => alert.id),
            bulk_action: "snooze",
            snooze_days: days,
          };

          this.$axios
            .post("alerts/bulk/", data)
            .then(r => {
              this.search();
              this.$q.loading.hide();
              this.notifySuccess(`Alerts were snoozed for ${days} days`);
            })
            .catch(e => {
              this.$q.loading.hide();
              this.notifyError("There was an error resolving alerts");
            });
        });
    },
    alertColor(severity) {
      if (severity === "error") {
        return "red";
      }
      if (severity === "warning") {
        return "orange";
      }
      if (severity === "info") {
        return "info";
      }
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
  mounted() {
    this.getClients();
  },
};
</script>
