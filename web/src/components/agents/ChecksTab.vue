<template>
  <div v-if="!selectedAgent" class="q-pa-sm">No agent selected</div>
  <div v-else>
    <q-table
      dense
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      class="tabs-tbl-sticky"
      :style="{ 'max-height': tabHeight }"
      :rows="checks"
      :columns="columns"
      row-key="id"
      binary-state-sort
      v-model:pagination="pagination"
      :loading="loading"
      :rows-per-page-options="[0]"
      virtual-scroll
      no-data-label="No checks"
    >
      <template v-slot:loading>
        <q-inner-loading showing color="primary" />
      </template>

      <!-- table top slot -->
      <template v-slot:top>
        <q-btn class="q-mr-sm" dense flat push @click="getChecks" icon="refresh" />
        <q-btn-dropdown icon="add" label="New" no-caps dense flat>
          <q-list dense style="min-width: 200px">
            <q-item v-if="agentPlatform === 'windows'" clickable v-close-popup @click="showCheckModal('diskspace')">
              <q-item-section side>
                <q-icon size="xs" name="far fa-hdd" />
              </q-item-section>
              <q-item-section>Disk Space Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showCheckModal('ping')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-network-wired" />
              </q-item-section>
              <q-item-section>Ping Check</q-item-section>
            </q-item>
            <q-item v-if="agentPlatform === 'windows'" clickable v-close-popup @click="showCheckModal('cpuload')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-microchip" />
              </q-item-section>
              <q-item-section>CPU Load Check</q-item-section>
            </q-item>
            <q-item v-if="agentPlatform === 'windows'" clickable v-close-popup @click="showCheckModal('memory')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-memory" />
              </q-item-section>
              <q-item-section>Memory Check</q-item-section>
            </q-item>
            <q-item v-if="agentPlatform === 'windows'" clickable v-close-popup @click="showCheckModal('winsvc')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-cogs" />
              </q-item-section>
              <q-item-section>Windows Service Check</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="showCheckModal('script')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-terminal" />
              </q-item-section>
              <q-item-section>Script Check</q-item-section>
            </q-item>
            <q-item v-if="agentPlatform === 'windows'" clickable v-close-popup @click="showCheckModal('eventlog')">
              <q-item-section side>
                <q-icon size="xs" name="fas fa-clipboard-list" />
              </q-item-section>
              <q-item-section>Event Log Check</q-item-section>
            </q-item>
          </q-list>
        </q-btn-dropdown>
      </template>

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
      <template v-slot:header-cell-dashboardalert="props">
        <q-th auto-width :props="props">
          <q-icon name="notifications" size="1.5em">
            <q-tooltip>Dashboard Alert</q-tooltip>
          </q-icon>
        </q-th>
      </template>
      <template v-slot:header-cell-statusicon="props">
        <q-th auto-width :props="props"></q-th>
      </template>
      <template v-slot:header-cell-policystatus="props">
        <q-th auto-width :props="props"></q-th>
      </template>

      <!-- body slots -->
      <template v-slot:body="props">
        <q-tr :props="props" class="cursor-pointer" @dblclick="showCheckModal(props.row.check_type, props.row)">
          <!-- context menu -->
          <q-menu context-menu>
            <q-list dense style="min-width: 200px">
              <q-item
                clickable
                v-close-popup
                @click="showCheckModal(props.row.check_type, props.row)"
                :disable="!!props.row.policy"
              >
                <q-item-section side>
                  <q-icon name="edit" />
                </q-item-section>
                <q-item-section>Edit</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="deleteCheck(props.row)" :disable="!!props.row.policy">
                <q-item-section side>
                  <q-icon name="delete" />
                </q-item-section>
                <q-item-section>Delete</q-item-section>
              </q-item>
              <q-separator></q-separator>
              <q-item clickable v-close-popup @click="resetCheckStatus(props.row)">
                <q-item-section side>
                  <q-icon name="info" />
                </q-item-section>
                <q-item-section>Reset Check Status</q-item-section>
              </q-item>
              <q-separator></q-separator>
              <q-item clickable v-close-popup>
                <q-item-section>Close</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
          <!-- tds -->
          <!-- text alert -->
          <q-td>
            <q-checkbox
              v-if="props.row.alert_template && props.row.alert_template.always_text != null"
              v-model="props.row.alert_template.always_text"
              disable
              dense
            >
              <q-tooltip> Setting is overridden by alert template: {{ props.row.alert_template.name }} </q-tooltip>
            </q-checkbox>

            <q-checkbox
              v-else
              dense
              @update:model-value="editCheck(props.row, { text_alert: !props.row.text_alert })"
              v-model="props.row.text_alert"
              :disable="!!props.row.policy"
            />
          </q-td>
          <!-- email alert -->
          <q-td>
            <q-checkbox
              v-if="props.row.alert_template && props.row.alert_template.always_email != null"
              v-model="props.row.alert_template.always_email"
              disable
              dense
            >
              <q-tooltip> Setting is overridden by alert template: {{ props.row.alert_template.name }} </q-tooltip>
            </q-checkbox>

            <q-checkbox
              v-else
              dense
              @update:model-value="editCheck(props.row, { email_alert: !props.row.email_alert })"
              v-model="props.row.email_alert"
              :disable="!!props.row.policy"
            />
          </q-td>
          <!-- dashboard alert -->
          <q-td>
            <q-checkbox
              v-if="props.row.alert_template && props.row.alert_template.always_alert !== null"
              v-model="props.row.alert_template.always_alert"
              disable
              dense
            >
              <q-tooltip> Setting is overridden by alert template: {{ props.row.alert_template.name }} </q-tooltip>
            </q-checkbox>

            <q-checkbox
              v-else
              dense
              @update:model-value="editCheck(props.row, { dashboard_alert: !props.row.dashboard_alert })"
              v-model="props.row.dashboard_alert"
              :disable="!!props.row.policy"
            />
          </q-td>
          <!-- policy check icon -->
          <q-td v-if="props.row.policy">
            <q-icon style="font-size: 1.3rem" name="policy">
              <q-tooltip>This check is managed by a policy</q-tooltip>
            </q-icon>
          </q-td>
          <q-td v-else-if="props.row.overridden_by_policy">
            <q-icon style="font-size: 1.3rem" name="remove_circle_outline">
              <q-tooltip>This check is overriden by a policy</q-tooltip>
            </q-icon>
          </q-td>
          <q-td v-else></q-td>
          <!-- status icon -->
          <q-td v-if="Object.keys(props.row.check_result).length === 0"></q-td>
          <q-td v-else-if="props.row.check_result.status === 'passing'">
            <q-icon style="font-size: 1.3rem" color="positive" name="check_circle">
              <q-tooltip>Passing</q-tooltip>
            </q-icon>
          </q-td>
          <q-td v-else-if="props.row.check_result.status === 'failing'">
            <q-icon v-if="getAlertSeverity(props.row) === 'info'" style="font-size: 1.3rem" color="info" name="info">
              <q-tooltip>Informational</q-tooltip>
            </q-icon>
            <q-icon
              v-else-if="getAlertSeverity(props.row) === 'warning'"
              style="font-size: 1.3rem"
              color="warning"
              name="warning"
            >
              <q-tooltip>Warning</q-tooltip>
            </q-icon>
            <q-icon v-else style="font-size: 1.3rem" color="negative" name="error">
              <q-tooltip>Error</q-tooltip>
            </q-icon>
          </q-td>
          <q-td v-else></q-td>
          <!-- check description -->
          <q-td>
            <span>
              {{ truncateText(props.row.readable_desc, 40) }}
              <q-tooltip v-if="props.row.readable_desc.length > 40">{{ props.row.readable_desc }}</q-tooltip>
            </span></q-td
          >
          <!-- more info -->
          <q-td>
            <span
              v-if="props.row.check_result.id"
              style="cursor: pointer; text-decoration: underline"
              class="text-primary"
              @click="showCheckGraphModal(props.row)"
              >Show Run History</span
            >
            &nbsp;&nbsp;&nbsp;
            <span
              v-if="props.row.check_type === 'ping' && props.row.check_result.id"
              style="cursor: pointer; text-decoration: underline"
              class="text-primary"
              @click="showPingInfo(props.row)"
              >Last Output</span
            >
            <span
              v-else-if="props.row.check_type === 'script' && props.row.check_result.id"
              style="cursor: pointer; text-decoration: underline"
              class="text-primary"
              @click="showScriptOutput(props.row.check_result)"
              >Last Output</span
            >
            <span
              v-else-if="props.row.check_type === 'eventlog' && props.row.check_result.id"
              style="cursor: pointer; text-decoration: underline"
              class="text-primary"
              @click="showEventInfo(props.row)"
              >Last Output</span
            >
            <span
              v-else-if="
                props.row.check_type === 'diskspace' || (props.row.check_type === 'winsvc' && props.row.check_result.id)
              "
              >{{ props.row.check_result.more_info }}</span
            >
          </q-td>
          <q-td>{{ props.row.check_result.last_run ? formatDate(props.row.check_result.last_run) : "Never" }}</q-td>
          <q-td v-if="props.row.assignedtasks.length > 1">{{ props.row.assignedtasks.length }} Tasks</q-td>
          <q-td v-else-if="props.row.assignedtasks.length === 1">{{ props.row.assignedtasks[0].name }}</q-td>
          <q-td v-else></q-td>
        </q-tr>
      </template>
    </q-table>
  </div>
</template>

<script>
// composition imports
import { ref, computed, watch, inject, onMounted } from "vue";
import { useStore } from "vuex";
import { useQuasar } from "quasar";
import { updateCheck, removeCheck, resetCheck } from "@/api/checks";
import { fetchAgentChecks } from "@/api/agents";
import { truncateText } from "@/utils/format";
import { notifySuccess, notifyWarning } from "@/utils/notify";

// ui imports
import DiskSpaceCheck from "@/components/checks/DiskSpaceCheck";
import MemCheck from "@/components/checks/MemCheck";
import CpuLoadCheck from "@/components/checks/CpuLoadCheck";
import PingCheck from "@/components/checks/PingCheck";
import WinSvcCheck from "@/components/checks/WinSvcCheck";
import EventLogCheck from "@/components/checks/EventLogCheck";
import ScriptCheck from "@/components/checks/ScriptCheck";
import ScriptOutput from "@/components/checks/ScriptOutput";
import EventLogCheckOutput from "@/components/checks/EventLogCheckOutput";
import CheckGraph from "@/components/graphs/CheckGraph";

// static data
const columns = [
  { name: "smsalert", field: "text_alert", align: "left" },
  { name: "emailalert", field: "email_alert", align: "left" },
  { name: "dashboardalert", field: "dashboard_alert", align: "left" },
  { name: "policystatus", align: "left" },
  { name: "statusicon", align: "left" },
  { name: "desc", field: "readable_desc", label: "Description", align: "left", sortable: true },
  {
    name: "moreinfo",
    label: "More Info",
    field: "more_info",
    align: "left",
    sortable: true,
  },
  {
    name: "datetime",
    label: "Last Run",
    field: "last_run",
    align: "left",
    sortable: true,
  },
  { name: "assignedtasks", label: "Assigned Tasks", field: "assigned_task", align: "left", sortable: true },
];

export default {
  name: "ChecksTab",
  setup(props) {
    // setup vuex
    const store = useStore();
    const selectedAgent = computed(() => store.state.selectedRow);
    const tabHeight = computed(() => store.state.tabHeight);
    const agentPlatform = computed(() => store.state.agentPlatform);
    const formatDate = computed(() => store.getters.formatDate);

    // setup quasar
    const $q = useQuasar();

    // inject function to refresh dashboard
    const refreshDashboard = inject("refreshDashboard");

    // setup checks tab logic
    const checks = ref([]);
    const loading = ref(false);
    const pagination = ref({
      rowsPerPage: 0,
      sortBy: "status",
      descending: false,
    });

    function getAlertSeverity(check) {
      if (check.check_result.alert_severity) {
        return check.check_result.alert_severity;
      } else {
        return check.alert_severity;
      }
    }

    async function getChecks() {
      loading.value = true;
      checks.value = await fetchAgentChecks(selectedAgent.value);
      loading.value = false;
    }

    async function editCheck(check, data) {
      if (check.policy) return;

      loading.value = false;
      try {
        const result = await updateCheck(check.id, data);
        await getChecks();
        notifySuccess(result);
      } catch (e) {
        console.error(e);
      }

      loading.value = false;
    }

    function deleteCheck(check) {
      $q.dialog({
        title: "Are you sure?",
        message: `Delete ${check.readable_desc}`,
        cancel: true,
        ok: { label: "Delete", color: "negative" },
        persistent: true,
      }).onOk(async () => {
        loading.value = true;
        try {
          const result = await removeCheck(check.id);
          await getChecks();
          notifySuccess(result);
        } catch (e) {
          console.error(e);
        }
        loading.value = false;
      });
    }

    async function resetCheckStatus(check) {
      // make sure there is a check result before sending
      if (!check.check_result.status) {
        notifyWarning("Check hasn't run yet");
      } else if (check.check_result.status === "passing") {
        notifyWarning("Check is already passing");
      }

      loading.value = true;
      try {
        const result = await resetCheck(check.check_result.id);
        await getChecks();
        notifySuccess(result);
        refreshDashboard(false /* clearTreeSelected */, false /* clearSubTable */);
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    function showEventInfo(data) {
      $q.dialog({
        component: EventLogCheckOutput,
        componentProps: {
          evtLogData: data,
        },
      });
    }

    function showCheckGraphModal(check) {
      $q.dialog({
        component: CheckGraph,
        componentProps: {
          check: check,
        },
      });
    }

    function showScriptOutput(script) {
      $q.dialog({
        component: ScriptOutput,
        componentProps: {
          scriptInfo: script,
        },
      });
    }

    function showPingInfo(check) {
      $q.dialog({
        title: check.readable_desc,
        style: "width: 50vw; max-width: 60vw",
        message: `<pre>${check.check_result.more_info}</pre>`,
        html: true,
      });
    }

    function showCheckModal(type, check) {
      if (check && check.policy) return;

      let component;

      if (type === "diskspace") component = DiskSpaceCheck;
      else if (type === "memory") component = MemCheck;
      else if (type === "cpuload") component = CpuLoadCheck;
      else if (type === "ping") component = PingCheck;
      else if (type === "winsvc") component = WinSvcCheck;
      else if (type === "eventlog") component = EventLogCheck;
      else if (type === "script") component = ScriptCheck;
      else return;

      $q.dialog({
        component: component,
        componentProps: {
          check: check,
          parent: !check ? { agent: selectedAgent.value } : undefined,
        },
      }).onOk(getChecks);
    }

    watch(selectedAgent, (newValue, oldValue) => {
      if (newValue) {
        getChecks();
      }
    });

    onMounted(() => {
      if (selectedAgent.value) getChecks();
    });

    return {
      // reactive data
      checks,
      loading,
      pagination,
      tabHeight,
      selectedAgent,
      agentPlatform,

      // non-reactive data
      columns,

      // methods
      getChecks,
      editCheck,
      deleteCheck,
      resetCheckStatus,
      truncateText,
      formatDate,
      getAlertSeverity,

      // dialogs
      showScriptOutput,
      showCheckModal,
      showCheckGraphModal,
      showEventInfo,
      showPingInfo,
    };
  },
};
</script>

