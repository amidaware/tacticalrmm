<template>
  <div class="q-pt-none q-pb-none q-pr-xs q-pl-xs">
    <q-table
      dense
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      class="agents-tbl-sticky"
      :style="{ 'max-height': agentTableHeight }"
      :data="frame"
      :filter="search"
      :filter-method="filterTable"
      :columns="columns"
      :visible-columns="visibleColumns"
      row-key="id"
      binary-state-sort
      virtual-scroll
      :pagination.sync="pagination"
      :rows-per-page-options="[0]"
      no-data-label="No Agents"
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
      <template v-slot:header-cell-dashboardalert="props">
        <q-th auto-width :props="props">
          <q-icon name="notifications" size="1.5em">
            <q-tooltip>Dashboard Alert</q-tooltip>
          </q-icon>
        </q-th>
      </template>
      <template v-slot:header-cell-checks-status="props">
        <q-th :props="props">
          <q-icon name="fas fa-check-double" size="1.2em">
            <q-tooltip>Checks Status</q-tooltip>
          </q-icon>
        </q-th>
      </template>
      <template v-slot:header-cell-patchespending="props">
        <q-th auto-width :props="props">
          <q-icon name="verified_user" size="1.5em">
            <q-tooltip>Patches Pending</q-tooltip>
          </q-icon>
        </q-th>
      </template>
      <template v-slot:header-cell-pendingactions="props">
        <q-th auto-width :props="props">
          <q-icon name="far fa-clock" size="1.5em">
            <q-tooltip>Pending Actions</q-tooltip>
          </q-icon>
        </q-th>
      </template>
      <template v-slot:header-cell-agentstatus="props">
        <q-th auto-width :props="props">
          <q-icon name="fas fa-signal" size="1.2em">
            <q-tooltip>Agent Status</q-tooltip>
          </q-icon>
        </q-th>
      </template>
      <template v-slot:header-cell-needs_reboot="props">
        <q-th auto-width :props="props">
          <q-icon name="fas fa-power-off" size="1.2em">
            <q-tooltip>Reboot</q-tooltip>
          </q-icon>
        </q-th>
      </template>
      <!-- body slots -->
      <template slot="body" slot-scope="props" :props="props">
        <q-tr
          @contextmenu="agentRowSelected(props.row.id, props.row.agent_id)"
          :props="props"
          :class="rowSelectedClass(props.row.id)"
          @click="agentRowSelected(props.row.id, props.row.agent_id)"
          @dblclick="rowDoubleClicked(props.row.id)"
        >
          <!-- context menu -->
          <q-menu context-menu>
            <q-list dense style="min-width: 200px">
              <!-- edit agent -->
              <q-item clickable v-close-popup @click="showEditAgentModal = true">
                <q-item-section side>
                  <q-icon size="xs" name="fas fa-edit" />
                </q-item-section>
                <q-item-section>Edit {{ props.row.hostname }}</q-item-section>
              </q-item>
              <!-- agent pending actions -->
              <q-item clickable v-close-popup @click="showPendingActionsModal(props.row.id)">
                <q-item-section side>
                  <q-icon size="xs" name="far fa-clock" />
                </q-item-section>
                <q-item-section>Pending Agent Actions</q-item-section>
              </q-item>
              <!-- take control -->
              <q-item clickable v-ripple v-close-popup @click.stop.prevent="takeControl(props.row.id)">
                <q-item-section side>
                  <q-icon size="xs" name="fas fa-desktop" />
                </q-item-section>

                <q-item-section>Take Control</q-item-section>
              </q-item>

              <q-item clickable v-ripple @click="getURLActions">
                <q-item-section side>
                  <q-icon size="xs" name="star" />
                </q-item-section>
                <q-item-section>Run URL Action</q-item-section>
                <q-item-section side>
                  <q-icon name="keyboard_arrow_right" />
                </q-item-section>
                <q-menu auto-close anchor="top end" self="top start">
                  <q-list>
                    <q-item
                      v-for="action in urlActions"
                      :key="action.id"
                      dense
                      clickable
                      v-close-popup
                      @click="runURLAction(props.row.id, action)"
                    >
                      {{ action.name }}
                    </q-item>
                  </q-list>
                </q-menu>
              </q-item>

              <q-item clickable v-ripple v-close-popup @click="showSendCommand = true">
                <q-item-section side>
                  <q-icon size="xs" name="fas fa-terminal" />
                </q-item-section>
                <q-item-section>Send Command</q-item-section>
              </q-item>

              <q-item clickable v-ripple v-close-popup @click="showRunScript = true">
                <q-item-section side>
                  <q-icon size="xs" name="fas fa-terminal" />
                </q-item-section>
                <q-item-section>Run Script</q-item-section>
              </q-item>

              <q-item clickable v-ripple @click="getFavoriteScripts">
                <q-item-section side>
                  <q-icon size="xs" name="star" />
                </q-item-section>
                <q-item-section>Run Favorited Script</q-item-section>
                <q-item-section side>
                  <q-icon name="keyboard_arrow_right" />
                </q-item-section>
                <q-menu auto-close anchor="top end" self="top start">
                  <q-list>
                    <q-item
                      v-for="script in favoriteScripts"
                      :key="script.value"
                      dense
                      clickable
                      v-close-popup
                      @click="runFavScript(script.value, props.row.id)"
                    >
                      {{ script.label }}
                    </q-item>
                  </q-list>
                </q-menu>
              </q-item>

              <q-item clickable v-close-popup @click.stop.prevent="remoteBG(props.row.id)">
                <q-item-section side>
                  <q-icon size="xs" name="fas fa-cogs" />
                </q-item-section>
                <q-item-section>Remote Background</q-item-section>
              </q-item>

              <!-- maintenance mode -->
              <q-item clickable @click="toggleMaintenance(props.row)">
                <q-item-section side>
                  <q-icon size="xs" name="construction" />
                </q-item-section>
                <q-item-section>{{ menuMaintenanceText(props.row.maintenance_mode) }}</q-item-section>
              </q-item>

              <!-- patch management -->
              <q-item clickable>
                <q-item-section side>
                  <q-icon size="xs" name="system_update" />
                </q-item-section>
                <q-item-section>Patch Management</q-item-section>
                <q-item-section side>
                  <q-icon name="keyboard_arrow_right" />
                </q-item-section>

                <q-menu anchor="top right" self="top left">
                  <q-list dense style="min-width: 100px">
                    <q-item
                      clickable
                      v-ripple
                      v-close-popup
                      @click.stop.prevent="runPatchStatusScan(props.row.id, props.row.hostname)"
                    >
                      <q-item-section>Run Patch Status Scan</q-item-section>
                    </q-item>
                    <q-item clickable v-ripple v-close-popup @click.stop.prevent="installPatches(props.row.id)">
                      <q-item-section>Install Patches Now</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
              </q-item>

              <q-item clickable v-close-popup @click.stop.prevent="runChecks(props.row.id)">
                <q-item-section side>
                  <q-icon size="xs" name="fas fa-check-double" />
                </q-item-section>
                <q-item-section>Run Checks</q-item-section>
              </q-item>

              <q-item clickable>
                <q-item-section side>
                  <q-icon size="xs" name="power_settings_new" />
                </q-item-section>
                <q-item-section>Reboot</q-item-section>
                <q-item-section side>
                  <q-icon name="keyboard_arrow_right" />
                </q-item-section>

                <q-menu anchor="top right" self="top left">
                  <q-list dense style="min-width: 100px">
                    <!-- reboot now -->
                    <q-item
                      clickable
                      v-ripple
                      v-close-popup
                      @click.stop.prevent="rebootNow(props.row.id, props.row.hostname)"
                    >
                      <q-item-section>Now</q-item-section>
                    </q-item>
                    <!-- reboot later -->
                    <q-item clickable v-ripple v-close-popup @click.stop.prevent="showRebootLaterModal = true">
                      <q-item-section>Later</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
              </q-item>

              <q-item clickable v-close-popup @click.stop.prevent="showPolicyAdd(props.row)">
                <q-item-section side>
                  <q-icon size="xs" name="policy" />
                </q-item-section>
                <q-item-section>Assign Automation Policy</q-item-section>
              </q-item>

              <q-item clickable v-close-popup @click.stop.prevent="showAgentRecovery = true">
                <q-item-section side>
                  <q-icon size="xs" name="fas fa-first-aid" />
                </q-item-section>
                <q-item-section>Agent Recovery</q-item-section>
              </q-item>

              <q-item clickable v-close-popup @click.stop.prevent="pingAgent(props.row.id)">
                <q-item-section side>
                  <q-icon size="xs" name="delete" />
                </q-item-section>
                <q-item-section>Remove Agent</q-item-section>
              </q-item>

              <q-separator />
              <q-item clickable v-close-popup>
                <q-item-section>Close</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
          <q-td>
            <q-checkbox
              v-if="props.row.alert_template && props.row.alert_template.always_text !== null"
              :value="props.row.alert_template.always_text"
              disable
              dense
            >
              <q-tooltip> Setting is overidden by alert template: {{ props.row.alert_template.name }} </q-tooltip>
            </q-checkbox>

            <q-checkbox
              v-else
              dense
              @input="overdueAlert('text', props.row.id, props.row.overdue_text_alert)"
              v-model="props.row.overdue_text_alert"
            />
          </q-td>
          <q-td>
            <q-checkbox
              v-if="props.row.alert_template && props.row.alert_template.always_email !== null"
              :value="props.row.alert_template.always_email"
              disable
              dense
            >
              <q-tooltip> Setting is overidden by alert template: {{ props.row.alert_template.name }} </q-tooltip>
            </q-checkbox>

            <q-checkbox
              v-else
              dense
              @input="overdueAlert('email', props.row.id, props.row.overdue_email_alert)"
              v-model="props.row.overdue_email_alert"
            />
          </q-td>
          <q-td>
            <q-checkbox
              v-if="props.row.alert_template && props.row.alert_template.always_alert !== null"
              :value="props.row.alert_template.always_alert"
              disable
              dense
            >
              <q-tooltip> Setting is overidden by alert template: {{ props.row.alert_template.name }} </q-tooltip>
            </q-checkbox>

            <q-checkbox
              v-else
              dense
              @input="overdueAlert('dashboard', props.row.id, props.row.overdue_dashboard_alert)"
              v-model="props.row.overdue_dashboard_alert"
            />
          </q-td>
          <q-td key="checks-status" :props="props">
            <q-icon v-if="props.row.maintenance_mode" name="construction" size="1.2em" color="green">
              <q-tooltip>Maintenance Mode Enabled</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.checks.failing > 0" name="fas fa-check-double" size="1.2em" color="negative">
              <q-tooltip>Checks failing</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.checks.warning > 0" name="fas fa-check-double" size="1.2em" color="warning">
              <q-tooltip>Checks warning</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.checks.info > 0" name="fas fa-check-double" size="1.2em" color="info">
              <q-tooltip>Checks info</q-tooltip>
            </q-icon>
            <q-icon v-else name="fas fa-check-double" size="1.2em" color="positive">
              <q-tooltip>Checks passing</q-tooltip>
            </q-icon>
          </q-td>
          <q-td key="client_name" :props="props">{{ props.row.client_name }}</q-td>
          <q-td key="site_name" :props="props">{{ props.row.site_name }}</q-td>

          <q-td key="hostname" :props="props">{{ props.row.hostname }}</q-td>
          <q-td key="description" :props="props">{{ props.row.description }}</q-td>
          <q-td key="user" :props="props">
            <span class="text-italic" v-if="props.row.italic">{{ props.row.logged_username }}</span>
            <span v-else>{{ props.row.logged_username }}</span>
          </q-td>
          <q-td :props="props" key="patchespending">
            <q-icon v-if="props.row.patches_pending" name="far fa-clock" color="primary">
              <q-tooltip>Patches Pending</q-tooltip>
            </q-icon>
          </q-td>
          <q-td :props="props" key="pendingactions">
            <q-icon
              v-if="props.row.pending_actions !== 0"
              @click="showPendingActionsModal(props.row.id)"
              name="far fa-clock"
              size="1.4em"
              color="warning"
              class="cursor-pointer"
            >
              <q-tooltip>Pending Action Count: {{ props.row.pending_actions }}</q-tooltip>
            </q-icon>
          </q-td>
          <!-- needs reboot -->
          <q-td key="needsreboot">
            <q-icon v-if="props.row.needs_reboot" name="fas fa-power-off" color="primary">
              <q-tooltip>Reboot required</q-tooltip>
            </q-icon>
          </q-td>
          <q-td key="agentstatus">
            <q-icon v-if="props.row.status === 'overdue'" name="fas fa-signal" size="1.2em" color="negative">
              <q-tooltip>Agent overdue</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.status === 'offline'" name="fas fa-signal" size="1.2em" color="warning">
              <q-tooltip>Agent offline</q-tooltip>
            </q-icon>
            <q-icon v-else name="fas fa-signal" size="1.2em" color="positive">
              <q-tooltip>Agent online</q-tooltip>
            </q-icon>
          </q-td>
          <q-td key="last_seen" :props="props">{{ formatDjangoDate(props.row.last_seen) }}</q-td>
          <q-td key="boot_time" :props="props">{{ bootTime(props.row.boot_time) }}</q-td>
        </q-tr>
      </template>
    </q-table>
    <q-inner-loading :showing="agentTableLoading">
      <q-spinner size="40px" color="primary" />
    </q-inner-loading>
    <!-- edit agent modal -->
    <q-dialog v-model="showEditAgentModal">
      <EditAgent @close="showEditAgentModal = false" @edited="agentEdited" />
    </q-dialog>
    <!-- reboot later modal -->
    <q-dialog v-model="showRebootLaterModal">
      <RebootLater @close="showRebootLaterModal = false" @edited="agentEdited" />
    </q-dialog>
    <!-- pending actions modal -->
    <div class="q-pa-md q-gutter-sm">
      <q-dialog v-model="showPendingActions" @hide="closePendingActionsModal">
        <PendingActions :agentpk="pendingActionAgentPk" @close="closePendingActionsModal" @edited="agentEdited" />
      </q-dialog>
    </div>
    <!-- send command modal -->
    <q-dialog v-model="showSendCommand" persistent>
      <SendCommand @close="showSendCommand = false" :pk="selectedAgentPk" />
    </q-dialog>
    <!-- agent recovery modal -->
    <q-dialog v-model="showAgentRecovery">
      <AgentRecovery @close="showAgentRecovery = false" :pk="selectedAgentPk" />
    </q-dialog>
    <!-- run script modal -->
    <q-dialog v-model="showRunScript" persistent>
      <RunScript @close="showRunScript = false" :pk="selectedAgentPk" />
    </q-dialog>
  </div>
</template>

<script>
import mixins from "@/mixins/mixins";
import { mapGetters } from "vuex";
import { date } from "quasar";
import EditAgent from "@/components/modals/agents/EditAgent";
import RebootLater from "@/components/modals/agents/RebootLater";
import PendingActions from "@/components/modals/logs/PendingActions";
import PolicyAdd from "@/components/automation/modals/PolicyAdd";
import SendCommand from "@/components/modals/agents/SendCommand";
import AgentRecovery from "@/components/modals/agents/AgentRecovery";
import RunScript from "@/components/modals/agents/RunScript";

export default {
  name: "AgentTable",
  props: ["frame", "columns", "tab", "userName", "search", "visibleColumns"],
  components: {
    EditAgent,
    RebootLater,
    PendingActions,
    SendCommand,
    AgentRecovery,
    RunScript,
  },
  mixins: [mixins],
  data() {
    return {
      pagination: {
        rowsPerPage: 0,
        sortBy: "hostname",
        descending: false,
      },
      showSendCommand: false,
      showEditAgentModal: false,
      showRebootLaterModal: false,
      showAgentRecovery: false,
      showRunScript: false,
      showPendingActions: false,
      pendingActionAgentPk: null,
      favoriteScripts: [],
      urlActions: [],
    };
  },
  methods: {
    filterTable(rows, terms, cols, cellValue) {
      const lowerTerms = terms ? terms.toLowerCase() : "";
      let advancedFilter = false;
      let availability = null;
      let checks = false;
      let patches = false;
      let actions = false;
      let reboot = false;
      let search = "";

      const params = lowerTerms.trim().split(" ");
      // parse search text and set variables
      params.forEach(param => {
        if (param.includes("is:")) {
          advancedFilter = true;
          let filter = param.split(":")[1];
          if (filter === "patchespending") patches = true;
          if (filter === "actionspending") actions = true;
          else if (filter === "checksfailing") checks = true;
          else if (filter === "rebootneeded") reboot = true;
          else if (filter === "online" || filter === "offline" || filter === "expired") availability = filter;
        } else {
          search = param + "";
        }
      });

      return rows.filter(row => {
        if (advancedFilter) {
          if (checks && !row.checks.has_failing_checks) return false;
          if (patches && !row.patches_pending) return false;
          if (actions && row.pending_actions === 0) return false;
          if (reboot && !row.needs_reboot) return false;
          if (availability === "online" && row.status !== "online") return false;
          else if (availability === "offline" && row.status !== "overdue") return false;
          else if (availability === "expired") {
            let now = new Date();
            let lastSeen = date.extractDate(row.last_seen, "MM DD YYYY HH:mm");
            let diff = date.getDateDiff(now, lastSeen, "days");
            if (diff < 30) return false;
          }
        }

        // Normal text filter
        return cols.some(col => {
          const val = cellValue(col, row) + "";
          const haystack = val === "undefined" || val === "null" ? "" : val.toLowerCase();
          return haystack.indexOf(search) !== -1;
        });
      });
    },
    rowDoubleClicked(pk) {
      this.$store.commit("setActiveRow", pk);
      this.$q.loading.show();
      // give time for store to change active row
      setTimeout(() => {
        this.$q.loading.hide();
        switch (this.agentDblClickAction) {
          case "editagent":
            this.showEditAgentModal = true;
            break;
          case "takecontrol":
            this.takeControl(pk);
            break;
          case "remotebg":
            this.remoteBG(pk);
            break;
        }
      }, 500);
    },
    runFavScript(scriptpk, agentpk) {
      const script = this.favoriteScripts.find(i => i.value === scriptpk);
      const data = {
        pk: agentpk,
        timeout: script.timeout,
        scriptPK: scriptpk,
        output: "forget",
        args: script.args,
      };
      this.$axios
        .post("/agents/runscript/", data)
        .then(r => this.notifySuccess(r.data))
        .catch(e => {});
    },
    getFavoriteScripts() {
      this.favoriteScripts = [];
      this.$axios
        .get("/scripts/scripts/")
        .then(r => {
          if (r.data.filter(k => k.favorite === true).length === 0) {
            this.notifyWarning("You don't have any scripts favorited!");
            return;
          }
          this.favoriteScripts = r.data
            .filter(k => k.favorite === true)
            .map(script => ({
              label: script.name,
              value: script.id,
              timeout: script.default_timeout,
              args: script.args,
            }))
            .sort((a, b) => a.label.localeCompare(b.label));
        })
        .catch(e => {});
    },
    runPatchStatusScan(pk, hostname) {
      this.$axios
        .get(`/winupdate/${pk}/runupdatescan/`)
        .then(r => {
          this.notifySuccess(`Scan will be run shortly on ${hostname}`);
        })
        .catch(e => {});
    },
    installPatches(pk) {
      this.$q.loading.show();
      this.$axios
        .get(`/winupdate/${pk}/installnow/`)
        .then(r => {
          this.$q.loading.hide();
          this.notifySuccess(r.data);
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    agentEdited() {
      this.$emit("refreshEdit");
    },
    showPendingActionsModal(pk) {
      this.showPendingActions = true;
      this.pendingActionAgentPk = pk;
    },
    closePendingActionsModal() {
      this.showPendingActions = false;
      this.pendingActionAgentPk = null;
    },
    takeControl(pk) {
      const url = this.$router.resolve(`/takecontrol/${pk}`).href;
      window.open(url, "", "scrollbars=no,location=no,status=no,toolbar=no,menubar=no,width=1600,height=900");
    },
    remoteBG(pk) {
      const url = this.$router.resolve(`/remotebackground/${pk}`).href;
      window.open(url, "", "scrollbars=no,location=no,status=no,toolbar=no,menubar=no,width=1280,height=826");
    },
    runChecks(pk) {
      this.$q.loading.show();
      this.$axios
        .get(`/checks/runchecks/${pk}/`)
        .then(r => {
          this.$q.loading.hide();
          this.notifySuccess(r.data);
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    removeAgent(pk, name) {
      this.$q
        .dialog({
          title: `Please type <code style="color:red">${name}</code> to confirm deletion.`,
          prompt: {
            model: "",
            type: "text",
            isValid: val => val === name,
          },
          cancel: true,
          ok: { label: "Uninstall", color: "negative" },
          persistent: true,
          html: true,
        })
        .onOk(val => {
          const data = { pk: pk };
          this.$axios
            .delete("/agents/uninstall/", { data: data })
            .then(r => {
              this.notifySuccess(r.data);
              setTimeout(() => {
                location.reload();
              }, 2000);
            })
            .catch(e => {});
        });
    },
    pingAgent(pk) {
      this.$q.loading.show();
      this.$axios
        .get(`/agents/${pk}/ping/`)
        .then(r => {
          this.$q.loading.hide();
          if (r.data.status === "offline") {
            this.$q
              .dialog({
                title: "Agent offline",
                message: `${r.data.name} cannot be contacted. 
                  Would you like to continue with the uninstall? 
                  If so, the agent will need to be manually uninstalled from the computer.`,
                cancel: { label: "No", color: "negative" },
                ok: { label: "Yes", color: "positive" },
                persistent: true,
              })
              .onOk(() => this.removeAgent(pk, r.data.name))
              .onCancel(() => {
                return;
              });
          } else if (r.data.status === "online") {
            this.removeAgent(pk, r.data.name);
          } else {
            this.notifyError("Something went wrong");
          }
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    rebootNow(pk, hostname) {
      this.$q
        .dialog({
          title: "Are you sure?",
          message: `Reboot ${hostname} now`,
          cancel: true,
          persistent: true,
        })
        .onOk(() => {
          this.$q.loading.show();
          this.$axios
            .post("/agents/reboot/", { pk: pk })
            .then(r => {
              this.$q.loading.hide();
              this.notifySuccess(`${hostname} will now be restarted`);
            })
            .catch(e => {
              this.$q.loading.hide();
            });
        });
    },
    agentRowSelected(pk) {
      this.$store.commit("setActiveRow", pk);
      this.$store.dispatch("loadSummary", pk);
      this.$store.dispatch("loadChecks", pk);
      this.$store.dispatch("loadAutomatedTasks", pk);
      this.$store.dispatch("loadWinUpdates", pk);
      this.$store.dispatch("loadInstalledSoftware", pk);
      this.$store.dispatch("loadNotes", pk);
    },
    overdueAlert(category, pk, alert_action) {
      let db_field = "";
      if (category === "email") db_field = "overdue_email_alert";
      else if (category === "text") db_field = "overdue_text_alert";
      else if (category === "dashboard") db_field = "overdue_dashboard_alert";

      const action = alert_action ? "enabled" : "disabled";
      const data = {
        pk: pk,
        [db_field]: alert_action,
      };
      const alertColor = alert_action ? "positive" : "warning";
      this.$axios
        .post("/agents/overdueaction/", data)
        .then(r => {
          this.$q.notify({
            color: alertColor,
            icon: "fas fa-check-circle",
            message: `Overdue ${category} alerts ${action} on ${r.data}`,
          });
        })
        .catch(e => {});
    },
    agentClass(status) {
      if (status === "offline") {
        return "agent-offline";
      } else if (status === "overdue") {
        return "agent-overdue";
      } else {
        return "agent-normal";
      }
    },
    showPolicyAdd(agent) {
      this.$q
        .dialog({
          component: PolicyAdd,
          parent: this,
          type: "agent",
          object: agent,
        })
        .onOk(() => {
          this.$emit("refreshEdit");
        });
    },
    toggleMaintenance(agent) {
      let data = {
        id: agent.id,
        type: "Agent",
        action: !agent.maintenance_mode,
      };

      const text = agent.maintenance_mode ? "Maintenance mode was disabled" : "Maintenance mode was enabled";
      this.$store.dispatch("toggleMaintenanceMode", data).then(response => {
        this.notifySuccess(text);
        this.$emit("refreshEdit");
      });
    },
    menuMaintenanceText(mode) {
      return mode ? "Disable Maintenance Mode" : "Enable Maintenance Mode";
    },
    rowSelectedClass(id) {
      if (this.selectedRow === id) return this.$q.dark.isActive ? "highlight-dark" : "highlight";
    },
    getURLActions() {
      this.$axios
        .get("/core/urlaction/")
        .then(r => {
          if (r.data.length === 0) {
            this.notifyWarning("No URL Actions configured. Go to Settings > Global Settings > URL Actions");
            return;
          }
          this.urlActions = r.data;
        })
        .catch(() => {});
    },
    runURLAction(agentid, action) {
      const data = {
        agent: agentid,
        action: action.id,
      };
      this.$axios
        .patch("/core/urlaction/run", data)
        .then(r => {})
        .catch(() => {});
    },
  },
  computed: {
    ...mapGetters(["selectedAgentPk", "agentTableHeight"]),
    agentDblClickAction() {
      return this.$store.state.agentDblClickAction;
    },
    selectedRow() {
      return this.$store.state.selectedRow;
    },
    agentTableLoading() {
      return this.$store.state.agentTableLoading;
    },
  },
};
</script>

