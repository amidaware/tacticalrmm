<template>
  <div class="q-pa-md">
    <q-table
      dense
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      class="remote-bg-tbl-sticky"
      :data="procs"
      :columns="columns"
      :pagination.sync="pagination"
      :filter="filter"
      row-key="id"
      binary-state-sort
      hide-bottom
    >
      <template v-slot:top>
        <q-btn v-if="poll" dense flat push @click="stopPoll" icon="stop" label="Stop Live Refresh" />
        <q-btn v-else dense flat push @click="startPoll" icon="play_arrow" label="Resume Live Refresh" />
        <q-space />
        <q-input v-model="filter" outlined label="Search" dense clearable>
          <template v-slot:prepend>
            <q-icon name="search" />
          </template>
        </q-input>
      </template>
      <template slot="body" slot-scope="props" :props="props">
        <q-tr :props="props">
          <q-menu context-menu>
            <q-list dense style="min-width: 200px">
              <q-item clickable v-close-popup @click="killProc(props.row.pid, props.row.name)">
                <q-item-section thumbnail>
                  <q-icon name="fas fa-trash-alt" size="xs" />
                </q-item-section>
                <q-item-section>End task</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
          <q-td>{{ props.row.name }}</q-td>
          <q-td>{{ Math.ceil(props.row.cpu_percent) }}%</q-td>
          <q-td>{{ convert(props.row.memory_percent) }} MB</q-td>
          <q-td>{{ props.row.username }}</q-td>
          <q-td>{{ props.row.pid }}</q-td>
          <q-td>{{ props.row.status }}</q-td>
        </q-tr>
      </template>
    </q-table>
  </div>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";

export default {
  name: "ProcessManager",
  props: ["pk"],
  mixins: [mixins],
  data() {
    return {
      polling: null,
      mem: null,
      poll: true,
      procs: [],
      filter: "",
      pagination: {
        rowsPerPage: 99999,
        sortBy: "cpu_percent",
        descending: true,
      },
      columns: [
        {
          name: "name",
          label: "Name",
          field: "name",
          align: "left",
          sortable: true,
        },
        {
          name: "cpu_percent",
          label: "CPU",
          field: "cpu_percent",
          align: "left",
          sortable: true,
        },
        {
          name: "memory_percent",
          label: "Memory",
          field: "memory_percent",
          align: "left",
          sortable: true,
        },
        {
          name: "username",
          label: "User",
          field: "username",
          align: "left",
          sortable: true,
        },
        {
          name: "pid",
          label: "PID",
          field: "pid",
          align: "left",
          sortable: true,
        },
        {
          name: "status",
          label: "Status",
          field: "status",
          align: "left",
          sortable: true,
        },
      ],
    };
  },
  methods: {
    getProcesses() {
      this.procs = [];
      this.$q.loading.show({ message: "Loading Processes..." });
      axios
        .get(`/agents/${this.pk}/getprocs/`)
        .then(r => {
          this.procs = r.data;
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data);
        });
    },
    refreshProcs() {
      this.polling = setInterval(() => {
        axios
          .get(`/agents/${this.pk}/getprocs/`)
          .then(r => (this.procs = r.data))
          .catch(() => this.notifyError("Unable to contact the agent"));
      }, 10000);
    },
    killProc(pid, name) {
      this.$q.loading.show({ message: `Attempting to kill process ${name}` });
      axios
        .get(`/agents/${this.pk}/${pid}/killproc/`)
        .then(r => {
          this.$q.loading.hide();
          this.notifySuccess(`${name} was terminated!`);
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data);
        });
    },
    stopPoll() {
      this.poll = false;
      clearInterval(this.polling);
    },
    startPoll() {
      this.poll = true;
      axios.get(`/agents/${this.pk}/getprocs/`).then(r => (this.procs = r.data));
      this.refreshProcs();
    },
    getAgent() {
      axios.get(`/agents/${this.pk}/agentdetail/`).then(r => (this.mem = r.data.total_ram));
    },
    convert(percent) {
      const mb = this.mem * 1024;
      return Math.ceil((percent * mb) / 100).toLocaleString();
    },
  },
  beforeDestroy() {
    clearInterval(this.polling);
  },
  created() {
    this.getAgent();
    // disable loading bar
    this.$q.loadingBar.setDefaults({ size: "0px" });

    this.getProcesses();
  },
  mounted() {
    this.refreshProcs();
  },
};
</script>