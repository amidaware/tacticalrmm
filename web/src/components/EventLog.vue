<template>
  <div class="q-pa-md">
    <div class="row">
      <div class="col-2">
        <q-select
          dense
          options-dense
          outlined
          v-model="days"
          :options="lastDays"
          :label="showDays"
          @input="getEventLog"
        />
      </div>
      <div class="col-7"></div>
      <div class="col-3">
        <code>{{ logType }} log total records: {{ totalRecords }}</code>
      </div>
    </div>
    <q-table
      dense
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      class="remote-bg-tbl-sticky"
      :rows="events"
      :columns="columns"
      :v-model:pagination="pagination"
      :filter="filter"
      row-key="uid"
      binary-state-sort
      hide-bottom
      virtual-scroll
    >
      <template v-slot:top>
        <q-btn dense flat push @click="getEventLog" icon="refresh" />
        <q-space />
        <q-radio v-model="logType" color="cyan" val="Application" label="Application" @input="getEventLog" />
        <q-radio v-model="logType" color="cyan" val="System" label="System" @input="getEventLog" />
        <q-radio v-model="logType" color="cyan" val="Security" label="Security" @input="getEventLog" />
        <q-space />
        <q-input v-model="filter" outlined label="Search" dense clearable>
          <template v-slot:prepend>
            <q-icon name="search" />
          </template>
        </q-input>
      </template>
      <template v-slot:body="props">
        <q-tr :props="props">
          <q-td>{{ props.row.eventType }}</q-td>
          <q-td>{{ props.row.source }}</q-td>
          <q-td>{{ props.row.eventID }}</q-td>
          <q-td>{{ props.row.time }}</q-td>
          <q-td @click.native="showFullMsg(props.row.message)">
            <span style="cursor: pointer; text-decoration: underline" class="text-primary">{{
              formatMessage(props.row.message)
            }}</span>
          </q-td>
        </q-tr>
      </template>
    </q-table>
  </div>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "EventLog",
  props: ["pk"],
  mixins: [mixins],
  data() {
    return {
      events: [],
      logType: "Application",
      days: 1,
      lastDays: [1, 2, 3, 4, 5, 10, 30, 60, 90, 180, 360, 9999],
      filter: "",
      pagination: {
        rowsPerPage: 0,
        sortBy: "record",
        descending: true,
      },
      columns: [
        { name: "eventType", label: "Type", field: "eventType", align: "left", sortable: true },
        { name: "source", label: "Source", field: "source", align: "left", sortable: true },
        { name: "eventID", label: "Event ID", field: "eventID", align: "left", sortable: true },
        { name: "time", label: "Time", field: "time", align: "left", sortable: true },
        { name: "message", label: "Message (click to view full)", field: "message", align: "left", sortable: true },
      ],
    };
  },
  computed: {
    totalRecords() {
      return this.events.length;
    },
    showDays() {
      return `Show last ${this.days} days`;
    },
  },
  methods: {
    formatMessage(msg) {
      return msg.substring(0, 60) + "...";
    },
    showFullMsg(msg) {
      this.$q.dialog({
        message: `<pre>${msg}</pre>`,
        html: true,
        fullWidth: true,
      });
    },
    getEventLog() {
      this.events = [];
      this.$q.loading.show({ message: `Loading ${this.logType} event log...please wait` });
      this.$axios
        .get(`/agents/${this.pk}/geteventlog/${this.logType}/${this.days}/`)
        .then(r => {
          this.events = Object.freeze(r.data);
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
  },
  created() {
    this.getEventLog();
  },
};
</script>