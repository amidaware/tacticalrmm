<template>
  <div class="row">
    <div class="col-12">
      <template v-if="tasks === undefined || tasks.length === 0">
        <p>No Tasks on this policy</p>
      </template>
      <template v-else>
        <q-table
          dense
          class="autotasks-tbl-sticky"
          :data="tasks"
          :columns="columns"
          :row-key="row => row.id"
          binary-state-sort
          :pagination.sync="pagination"
          hide-bottom
        >
          <!-- header slots -->
          <template v-slot:header-cell-enabled="props">
            <q-th auto-width :props="props">
              <small>Enabled</small>
            </q-th>
          </template>
          <!-- body slots -->
          <template slot="body" slot-scope="props" :props="props">
            <q-tr>
              <!-- tds -->
              <q-td>
                <q-checkbox
                  disabled
                  dense
                  v-model="props.row.enabled"
                />
              </q-td>
              <q-td>{{ props.row.name }}</q-td>
              <q-td v-if="props.row.retcode || props.row.stdout || props.row.stderr">
                <span
                  style="cursor:pointer;color:blue;text-decoration:underline"
                >output</span>
              </q-td>
              <q-td v-else>Awaiting output</q-td>
              <q-td v-if="props.row.last_run">{{ props.row.last_run }}</q-td>
              <q-td v-else>Has not run yet</q-td>
              <q-td>{{ props.row.schedule }}</q-td>
              <q-td>{{ props.row.assigned_check }}</q-td>
            </q-tr>
          </template>
        </q-table>
      </template>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";

export default {
  name: "OverviewAutomatedTasksTab",
  props: ["policypk"],
  mixins: [mixins],
  data () {
    return {
      automatedTasks: {},
      columns: [
        { name: "enabled", align: "left", field: "enabled" },
        { name: "name", label: "Name", field: "name", align: "left" },
        {
          name: "moreinfo",
          label: "More Info",
          field: "more_info",
          align: "left"
        },
        {
          name: "datetime",
          label: "Last Run Time",
          field: "last_run",
          align: "left"
        },
        {
          name: "schedule",
          label: "Schedule",
          field: "schedule",
          align: "left"
        },
        {
          name: "assignedcheck",
          label: "Assigned Check",
          field: "assigned_check",
          align: "left"
        }
      ],
      pagination: {
        rowsPerPage: 9999
      }
    };
  },
 mounted () {
    this.getPolicyTasks();
  },
  watch: {
    'policypk': function () {
      this.getPolicyTasks();
    }
  },
  methods: {
    getPolicyTasks () {
      axios.get(`/automation/${this.policypk}/policyautomatedtasks/`).then(r => {
        this.automatedTasks = r.data;
      })
      .catch(e => {
        this.$q.loading.hide();
        this.notifyError(e.response.data);
      });
    }
  },
  computed: {
    tasks () {
      return this.automatedTasks.autotasks;
    }
  }
};
</script>

<style lang="stylus">
.autotasks-tbl-sticky {
  .q-table__middle {
    max-height: 25vh;
  }

  .q-table__top, .q-table__bottom, thead tr:first-child th {
    background-color: #f5f4f2;
  }

  thead tr:first-child th {
    position: sticky;
    top: 0;
    opacity: 1;
    z-index: 1;
  }
}
</style>

