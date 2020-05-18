<template>
  <div class="row">
    <div class="col-12">
      <template v-if="Object.keys(checks).length === 0 || allChecks.length === 0">
        <p>No checks on this policy</p>
      </template>
      <template v-else>
        <q-table
          dense
          class="tabs-tbl-sticky"
          :data="allChecks"
          :columns="columns"
          :row-key="row => row.id + row.check_type"
          binary-state-sort
          :pagination.sync="pagination"
          hide-bottom
        >
          <!-- header slots -->
          <template v-slot:header-cell-smsalert="props">
            <q-th auto-width :props="props">
              <q-icon name="phone_android" size="1.5em">
                <q-tooltip>SMS Alert</q-tooltip>
              </q-icon>
            </q-th>
          </template>
          <template v-slot:header-cell-emailalert="props">
            <q-th auto-width :props="props">
              <q-icon name="email" size="1.5em">
                <q-tooltip>Email Alert</q-tooltip>
              </q-icon>
            </q-th>
          </template>
          <template v-slot:header-cell-statusicon="props">
            <q-th auto-width :props="props"></q-th>
          </template>
          <!-- body slots -->
          <template slot="body" slot-scope="props" :props="props">
            <q-tr>
              <!-- tds -->
              <q-td>
                <q-checkbox disabled dense v-model="props.row.text_alert" />
              </q-td>
              <q-td>
                <q-checkbox disabled dense v-model="props.row.email_alert" />
              </q-td>
              <q-td v-if="props.row.status === 'pending'"></q-td>
              <q-td v-else-if="props.row.status === 'passing'">
                <q-icon style="font-size: 1.3rem;" color="positive" name="check_circle" />
              </q-td>
              <q-td v-else-if="props.row.status === 'failing'">
                <q-icon style="font-size: 1.3rem;" color="negative" name="error" />
              </q-td>
              <q-td
                v-if="props.row.check_type === 'diskspace'"
              >Disk Space Drive {{ props.row.disk }} > {{props.row.threshold }}%</q-td>
              <q-td
                v-else-if="props.row.check_type === 'cpuload'"
              >Avg CPU Load > {{ props.row.cpuload }}%</q-td>
              <q-td
                v-else-if="props.row.check_type === 'script'"
              >Script check: {{ props.row.script.name }}</q-td>
              <q-td
                v-else-if="props.row.check_type === 'ping'"
              >Ping {{ props.row.name }} ({{ props.row.ip }})</q-td>
              <q-td
                v-else-if="props.row.check_type === 'memory'"
              >Avg memory usage > {{ props.row.threshold }}%</q-td>
              <q-td
                v-else-if="props.row.check_type === 'winsvc'"
              >Service Check - {{ props.row.svc_display_name }}</q-td>
              <q-td v-if="props.row.status === 'pending'">Awaiting First Synchronization</q-td>
              <q-td v-else-if="props.row.status === 'passing'">
                <q-badge color="positive">Passing</q-badge>
              </q-td>
              <q-td v-else-if="props.row.status === 'failing'">
                <q-badge color="negative">Failing</q-badge>
              </q-td>
              <q-td v-if="props.row.check_type === 'ping'">
                <span style="cursor:pointer;color:blue;text-decoration:underline">output</span>
              </q-td>
              <q-td v-else-if="props.row.check_type === 'script'">
                <span style="cursor:pointer;color:blue;text-decoration:underline">output</span>
              </q-td>
              <q-td v-else>{{ props.row.more_info }}</q-td>
              <q-td>{{ props.row.last_run }}</q-td>
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
  name: "OverviewChecksTab",
  props: ["policypk"],
  mixins: [mixins],
  data() {
    return {
      checks: {},
      columns: [
        { name: "smsalert", field: "text_alert", align: "left" },
        { name: "emailalert", field: "email_alert", align: "left" },
        { name: "statusicon", align: "left" },
        { name: "desc", label: "Description", align: "left" },
        { name: "status", label: "Status", field: "status", align: "left" },
        {
          name: "moreinfo",
          label: "More Info",
          field: "more_info",
          align: "left"
        },
        {
          name: "datetime",
          label: "Date / Time",
          field: "last_run",
          align: "left"
        }
      ],
      pagination: {
        rowsPerPage: 9999
      }
    };
  },
  mounted() {
    this.getPolicyChecks();
  },
  watch: {
    policypk: function() {
      this.getPolicyChecks();
    }
  },
  methods: {
    getPolicyChecks() {
      axios
        .get(`/checks/${this.policypk}/loadpolicychecks/`)
        .then(r => {
          this.checks = r.data;
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data);
        });
    }
  },
  computed: {
    allChecks() {
      return [
        ...this.checks.diskchecks,
        ...this.checks.cpuloadchecks,
        ...this.checks.memchecks,
        ...this.checks.scriptchecks,
        ...this.checks.winservicechecks,
        ...this.checks.pingchecks
      ];
    }
  }
};
</script>

