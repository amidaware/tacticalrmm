<template>
  <div class="q-pa-none">
    <q-table
      dense
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      class="agents-tbl-sticky"
      :table-style="{ 'max-height': agentTableHeight }"
      :rows="frame"
      :filter="search"
      :filter-method="filterTable"
      :columns="columns"
      :visible-columns="visibleColumns"
      row-key="id"
      binary-state-sort
      virtual-scroll
      v-model:pagination="pagination"
      :rows-per-page-options="[0]"
      no-data-label="No Agents"
      :loading="agentTableLoading"
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
      <template v-slot:body="props">
        <q-tr
          @contextmenu="agentRowSelected(props.row.agent_id)"
          :props="props"
          :class="rowSelectedClass(props.row.agent_id)"
          @click="agentRowSelected(props.row.agent_id)"
          @dblclick="rowDoubleClicked(props.row.agent_id)"
        >
          <!-- context menu -->
          <q-menu context-menu>
            <q-list dense style="min-width: 200px">
              <!-- edit agent -->
              <q-item clickable v-close-popup @click="showEditAgent(props.row.agent_id)">
                <q-item-section side>
                  <q-icon size="xs" name="fas fa-edit" />
                </q-item-section>
                <q-item-section>Edit {{ props.row.hostname }}</q-item-section>
              </q-item>
              <!-- agent pending actions -->
              <q-item clickable v-close-popup @click="showPendingActionsModal(props.row)">
                <q-item-section side>
                  <q-icon size="xs" name="far fa-clock" />
                </q-item-section>
                <q-item-section>Pending Agent Actions</q-item-section>
              </q-item>
              <!-- take control -->
              <q-item clickable v-ripple v-close-popup @click.stop.prevent="takeControl(props.row.agent_id)">
                <q-item-section side>
                  <q-icon size="xs" name="fas fa-desktop" />
                </q-item-section>

                <q-item-section>Take Control</q-item-section>
              </q-item>

              <q-item clickable v-ripple @click="getURLActions">
                <q-item-section side>
                  <q-icon size="xs" name="open_in_new" />
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
                      @click="runURLAction(props.row.agent_id, action.id)"
                    >
                      {{ action.name }}
                    </q-item>
                  </q-list>
                </q-menu>
              </q-item>

              <q-item clickable v-ripple v-close-popup @click="showSendCommand(props.row)">
                <q-item-section side>
                  <q-icon size="xs" name="fas fa-terminal" />
                </q-item-section>
                <q-item-section>Send Command</q-item-section>
              </q-item>

              <q-item clickable v-ripple v-close-popup @click="showRunScript(props.row)">
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
                      @click="showRunScript(props.row, script.value)"
                    >
                      {{ script.label }}
                    </q-item>
                  </q-list>
                </q-menu>
              </q-item>

              <q-item clickable v-close-popup @click.stop.prevent="remoteBG(props.row.agent_id)">
                <q-item-section side>
                  <q-icon size="xs" name="fas fa-cogs" />
                </q-item-section>
                <q-item-section>Remote Background</q-item-section>
              </q-item>

              <!-- maintenance mode -->
              <q-item clickable v-close-popup @click="toggleMaintenance(props.row)">
                <q-item-section side>
                  <q-icon size="xs" name="construction" />
                </q-item-section>
                <q-item-section>
                  {{ props.row.maintenance_mode ? "Disable Maintenance Mode" : "Enable Maintenance Mode" }}
                </q-item-section>
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
                    <q-item clickable v-ripple v-close-popup @click.stop.prevent="runPatchStatusScan(props.row)">
                      <q-item-section>Run Patch Status Scan</q-item-section>
                    </q-item>
                    <q-item clickable v-ripple v-close-popup @click.stop.prevent="installPatches(props.row)">
                      <q-item-section>Install Patches Now</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
              </q-item>

              <q-item clickable v-close-popup @click.stop.prevent="runChecks(props.row)">
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
                    <q-item clickable v-ripple v-close-popup @click.stop.prevent="rebootNow(props.row)">
                      <q-item-section>Now</q-item-section>
                    </q-item>
                    <!-- reboot later -->
                    <q-item clickable v-ripple v-close-popup @click.stop.prevent="showRebootLaterModal(props.row)">
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

              <q-item clickable v-close-popup @click.stop.prevent="showAgentRecovery(props.row)">
                <q-item-section side>
                  <q-icon size="xs" name="fas fa-first-aid" />
                </q-item-section>
                <q-item-section>Agent Recovery</q-item-section>
              </q-item>

              <q-item clickable v-close-popup @click.stop.prevent="pingAgent(props.row)">
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
              v-model="props.row.alert_template.always_text"
              disable
              dense
            >
              <q-tooltip> Setting is overidden by alert template: {{ props.row.alert_template.name }} </q-tooltip>
            </q-checkbox>

            <q-checkbox
              v-else
              dense
              @update:model-value="overdueAlert('text', props.row, props.row.overdue_text_alert)"
              v-model="props.row.overdue_text_alert"
            />
          </q-td>
          <q-td>
            <q-checkbox
              v-if="props.row.alert_template && props.row.alert_template.always_email !== null"
              v-model="props.row.alert_template.always_email"
              disable
              dense
            >
              <q-tooltip> Setting is overidden by alert template: {{ props.row.alert_template.name }} </q-tooltip>
            </q-checkbox>

            <q-checkbox
              v-else
              dense
              @update:model-value="overdueAlert('email', props.row, props.row.overdue_email_alert)"
              v-model="props.row.overdue_email_alert"
            />
          </q-td>
          <q-td>
            <q-checkbox
              v-if="props.row.alert_template && props.row.alert_template.always_alert !== null"
              v-model="props.row.alert_template.always_alert"
              disable
              dense
            >
              <q-tooltip> Setting is overidden by alert template: {{ props.row.alert_template.name }} </q-tooltip>
            </q-checkbox>

            <q-checkbox
              v-else
              dense
              @update:model-value="overdueAlert('dashboard', props.row, props.row.overdue_dashboard_alert)"
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
            <q-icon v-if="props.row.has_patches_pending" name="verified_user" size="1.5em" color="primary">
              <q-tooltip>Patches Pending</q-tooltip>
            </q-icon>
          </q-td>
          <q-td :props="props" key="pendingactions">
            <q-icon
              v-if="props.row.pending_actions_count !== 0"
              @click="showPendingActionsModal(props.row)"
              name="far fa-clock"
              size="1.4em"
              color="warning"
              class="cursor-pointer"
            >
              <q-tooltip>Pending Action Count: {{ props.row.pending_actions_count }}</q-tooltip>
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
  </div>
</template>

<script>
import mixins from "@/mixins/mixins";
import { mapGetters } from "vuex";
import { date, openURL } from "quasar";
import EditAgent from "@/components/modals/agents/EditAgent";
import RebootLater from "@/components/modals/agents/RebootLater";
import PendingActions from "@/components/logs/PendingActions";
import PolicyAdd from "@/components/automation/modals/PolicyAdd";
import SendCommand from "@/components/modals/agents/SendCommand";
import AgentRecovery from "@/components/modals/agents/AgentRecovery";
import RunScript from "@/components/modals/agents/RunScript";

export default {
  name: "AgentTable",
  props: ["frame", "columns", "userName", "search", "visibleColumns"],
  inject: ["refreshDashboard"],
  mixins: [mixins],
  data() {
    return {
      pagination: {
        rowsPerPage: 0,
        sortBy: "hostname",
        descending: false,
      },
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
          else if (filter === "online" || filter === "offline" || filter === "expired" || filter === "overdue")
            availability = filter;
        } else {
          search = param + "";
        }
      });

      return rows.filter(row => {
        if (advancedFilter) {
          if (checks && !row.checks.has_failing_checks) return false;
          if (patches && !row.has_patches_pending) return false;
          if (actions && row.pending_actions_count === 0) return false;
          if (reboot && !row.needs_reboot) return false;
          if (availability === "online" && row.status !== "online") return false;
          else if (availability === "offline" && row.status !== "offline") return false;
          else if (availability === "overdue" && row.status !== "overdue") return false;
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
    rowDoubleClicked(agent_id) {
      this.$store.commit("setActiveRow", agent_id);
      this.$q.loading.show();
      // give time for store to change active row
      setTimeout(() => {
        this.$q.loading.hide();
        switch (this.agentDblClickAction) {
          case "editagent":
            this.showEditAgent(agent_id);
            break;
          case "takecontrol":
            this.takeControl(agent_id);
            break;
          case "remotebg":
            this.remoteBG(agent_id);
            break;
          case "urlaction":
            this.runURLAction(agent_id, this.agentUrlAction);
            break;
        }
      }, 500);
    },
    getFavoriteScripts() {
      this.favoriteScripts = [];
      this.$axios
        .get("/scripts/", { params: { showCommunityScripts: this.showCommunityScripts } })
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
    runPatchStatusScan(agent) {
      this.$axios
        .post(`/winupdate/${agent.agent_id}/scan/`)
        .then(r => {
          this.notifySuccess(`Scan will be run shortly on ${agent.hostname}`);
        })
        .catch(e => {});
    },
    installPatches(agent) {
      this.$q.loading.show();
      this.$axios
        .post(`/winupdate/${agent.agent_id}/install/`)
        .then(r => {
          this.$q.loading.hide();
          this.notifySuccess(r.data);
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    showPendingActionsModal(agent) {
      this.$q
        .dialog({
          component: PendingActions,
          componentProps: {
            agent: agent,
          },
        })
        .onDismiss(this.refreshDashboard);
    },
    takeControl(agent_id) {
      const url = this.$router.resolve(`/takecontrol/${agent_id}`).href;
      window.open(url, "", "scrollbars=no,location=no,status=no,toolbar=no,menubar=no,width=1600,height=900");
    },
    remoteBG(agent_id) {
      const url = this.$router.resolve(`/remotebackground/${agent_id}`).href;
      window.open(url, "", "scrollbars=no,location=no,status=no,toolbar=no,menubar=no,width=1280,height=826");
    },
    runChecks(agent) {
      this.$q.loading.show();
      this.$axios
        .get(`/checks/${agent.agent_id}/run/`)
        .then(r => {
          this.$q.loading.hide();
          this.notifySuccess(r.data);
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    removeAgent(agent) {
      this.$q
        .dialog({
          title: `Please type <code style="color:red">${agent.hostname}</code> to confirm deletion.`,
          prompt: {
            model: "",
            type: "text",
            isValid: val => val === agent.hostname,
          },
          cancel: true,
          ok: { label: "Uninstall", color: "negative" },
          persistent: true,
          html: true,
        })
        .onOk(val => {
          this.$q.loading.show();
          this.$axios
            .delete(`/agents/${agent.agent_id}/`)
            .then(r => {
              this.$q.loading.hide();
              this.notifySuccess(r.data);
              this.refreshDashboard();
            })
            .catch(e => {
              this.$q.loading.hide();
            });
        });
    },
    pingAgent(agent) {
      this.$q.loading.show();
      this.$axios
        .get(`/agents/${agent.agent_id}/ping/`)
        .then(r => {
          this.$q.loading.hide();
          if (r.data.status === "offline") {
            this.$q
              .dialog({
                title: "Agent offline",
                message: `${agent.hostname} cannot be contacted. 
                  Would you like to continue with the uninstall? 
                  If so, the agent will need to be manually uninstalled from the computer.`,
                cancel: { label: "No", color: "negative" },
                ok: { label: "Yes", color: "positive" },
                persistent: true,
              })
              .onOk(() => this.removeAgent(agent))
              .onCancel(() => {
                return;
              });
          } else if (r.data.status === "online") {
            this.removeAgent(agent);
          } else {
            this.notifyError("Something went wrong");
          }
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    rebootNow(agent) {
      this.$q
        .dialog({
          title: "Are you sure?",
          message: `Reboot ${agent.hostname} now`,
          cancel: true,
          persistent: true,
        })
        .onOk(() => {
          this.$q.loading.show();
          this.$axios
            .post(`/agents/${agent.agent_id}/reboot/`)
            .then(r => {
              this.$q.loading.hide();
              this.notifySuccess(`${agent.hostname} will now be restarted`);
            })
            .catch(e => {
              this.$q.loading.hide();
            });
        });
    },
    agentRowSelected(agent_id) {
      this.$store.commit("setActiveRow", agent_id);
    },
    overdueAlert(category, agent, alert_action) {
      let db_field = "";
      if (category === "email") db_field = "overdue_email_alert";
      else if (category === "text") db_field = "overdue_text_alert";
      else if (category === "dashboard") db_field = "overdue_dashboard_alert";

      const action = !alert_action ? "enabled" : "disabled";
      const data = {
        [db_field]: !alert_action,
      };
      const alertColor = !alert_action ? "positive" : "warning";
      this.$axios
        .put(`/agents/${agent.agent_id}/`, data)
        .then(r => {
          this.$q.notify({
            color: alertColor,
            icon: "fas fa-check-circle",
            message: `Overdue ${category} alerts ${action} on ${agent.hostname}`,
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
          componentProps: {
            type: "agent",
            object: agent,
          },
        })
        .onOk(this.refreshDashboard);
    },
    toggleMaintenance(agent) {
      let data = {
        maintenance_mode: !agent.maintenance_mode,
      };

      this.$axios
        .put(`/agents/${agent.agent_id}/`, data)
        .then(r => {
          this.notifySuccess(
            `Maintenance mode was ${agent.maintenance_mode ? "disabled" : "enabled"} on ${agent.hostname}`
          );
          this.refreshDashboard();
        })
        .catch(e => {
          console.log(e);
        });
    },
    rowSelectedClass(agent_id) {
      if (agent_id === this.selectedRow) {
        return this.$q.dark.isActive ? "highlight-dark" : "highlight";
      } else {
        return "";
      }
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
    runURLAction(agent_id, action) {
      const data = {
        agent_id: agent_id,
        action: action,
      };
      this.$axios
        .patch("/core/urlaction/run/", data)
        .then(r => {
          openURL(r.data);
        })
        .catch(() => {});
    },
    showRunScript(agent, script = undefined) {
      this.$q.dialog({
        component: RunScript,
        componentProps: {
          agent,
          script,
        },
      });
    },
    showSendCommand(agent) {
      this.$q.dialog({
        component: SendCommand,
        componentProps: {
          agent: agent,
        },
      });
    },
    showRebootLaterModal(agent) {
      this.$q
        .dialog({
          component: RebootLater,
          componentProps: {
            agent: agent,
          },
        })
        .onOk(this.refreshDashboard);
    },
    showEditAgent(agent_id) {
      this.$q
        .dialog({
          component: EditAgent,
          componentProps: {
            agent_id: agent_id,
          },
        })
        .onOk(this.refreshDashboard);
    },
    showAgentRecovery(agent) {
      this.$q.dialog({
        component: AgentRecovery,
        componentProps: {
          agent: agent,
        },
      });
    },
  },
  computed: {
    ...mapGetters(["agentTableHeight", "showCommunityScripts"]),
    agentDblClickAction() {
      return this.$store.state.agentDblClickAction;
    },
    agentUrlAction() {
      return this.$store.state.agentUrlAction;
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

