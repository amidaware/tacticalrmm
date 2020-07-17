<template>
  <div class="q-pa-sm">
    <q-table
      dense
      class="agents-tbl-sticky"
      :data="filter"
      :columns="columns"
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
      <!--
      <template v-slot:header-cell-antivirus="props">
        <q-th auto-width :props="props">
          <q-icon name="fas fa-shield-alt" size="1.2em" color="primary"><q-tooltip>Anti Virus</q-tooltip></q-icon>
        </q-th>
      </template>-->
      <template v-slot:header-cell-agentstatus="props">
        <q-th auto-width :props="props">
          <q-icon name="fas fa-signal" size="1.2em">
            <q-tooltip>Agent Status</q-tooltip>
          </q-icon>
        </q-th>
      </template>
      <template v-slot:header-cell-needsreboot="props">
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
          :class="{highlight: selectedRow === props.row.id}"
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
              <q-item
                clickable
                v-close-popup
                @click="showPendingActions(props.row.id, props.row.hostname)"
              >
                <q-item-section side>
                  <q-icon size="xs" name="far fa-clock" />
                </q-item-section>
                <q-item-section>Pending Agent Actions</q-item-section>
              </q-item>
              <!-- take control -->
              <q-item
                clickable
                v-ripple
                v-close-popup
                @click.stop.prevent="takeControl(props.row.id)"
              >
                <q-item-section side>
                  <q-icon size="xs" name="fas fa-desktop" />
                </q-item-section>

                <q-item-section>Take Control</q-item-section>
              </q-item>

              <!-- web rdp -->
              <q-item clickable v-ripple v-close-popup @click.stop.prevent="webRDP(props.row.id)">
                <q-item-section side>
                  <q-icon size="xs" name="screen_share" />
                </q-item-section>
                <q-item-section>Remote Desktop</q-item-section>
              </q-item>

              <q-item clickable v-ripple v-close-popup @click="showSendCommand = true">
                <q-item-section side>
                  <q-icon size="xs" name="fas fa-terminal" />
                </q-item-section>
                <q-item-section>Send Command</q-item-section>
              </q-item>

              <q-separator />
              <q-item clickable v-close-popup @click.stop.prevent="remoteBG(props.row.id)">
                <q-item-section side>
                  <q-icon size="xs" name="fas fa-cogs" />
                </q-item-section>
                <q-item-section>Remote Background</q-item-section>
              </q-item>

              <!-- patch management -->
              <q-separator />
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
                    <q-item
                      clickable
                      v-ripple
                      v-close-popup
                      @click.stop.prevent="installPatches(props.row.id)"
                    >
                      <q-item-section>Install Patches Now</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
              </q-item>
              <q-separator />
              <q-item clickable v-close-popup @click.stop.prevent="runChecks(props.row.id)">
                <q-item-section side>
                  <q-icon size="xs" name="fas fa-check-double" />
                </q-item-section>
                <q-item-section>Run Checks</q-item-section>
              </q-item>

              <q-separator />
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
                    <q-item
                      clickable
                      v-ripple
                      v-close-popup
                      @click.stop.prevent="showRebootLaterModal = true"
                    >
                      <q-item-section>Later</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
              </q-item>

              <q-separator />
              <q-item clickable v-close-popup @click.stop.prevent="showPolicyAdd(props.row.id)">
                <q-item-section side>
                  <q-icon size="xs" name="policy" />
                </q-item-section>
                <q-item-section>Edit Policies</q-item-section>
              </q-item>

              <q-separator />
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
              dense
              @input="overdueAlert('text', props.row.id, props.row.overdue_text_alert)"
              v-model="props.row.overdue_text_alert"
            />
          </q-td>
          <q-td>
            <q-checkbox
              dense
              @input="overdueAlert('email', props.row.id, props.row.overdue_email_alert)"
              v-model="props.row.overdue_email_alert"
            />
          </q-td>
          <q-td key="checks-status" :props="props">
            <q-icon
              v-if="props.row.checks.has_failing_checks"
              name="fas fa-check-double"
              size="1.2em"
              color="negative"
            >
              <q-tooltip>Checks failing</q-tooltip>
            </q-icon>
            <q-icon v-else name="fas fa-check-double" size="1.2em" color="positive">
              <q-tooltip>Checks passing</q-tooltip>
            </q-icon>
          </q-td>
          <q-td key="client" :props="props">{{ props.row.client }}</q-td>
          <q-td key="site" :props="props">{{ props.row.site }}</q-td>

          <q-td key="hostname" :props="props">{{ props.row.hostname }}</q-td>
          <q-td key="description" :props="props">{{ props.row.description }}</q-td>
          <q-td key="user" :props="props">
            <span v-if="props.row.logged_in_username !== 'None'">{{ props.row.logged_in_username }}</span>
            <span v-else>-</span>
          </q-td>
          <q-td :props="props" key="patchespending">
            <q-icon v-if="props.row.patches_pending" name="far fa-clock" color="primary">
              <q-tooltip>Patches Pending</q-tooltip>
            </q-icon>
          </q-td>
          <!--
          <q-td :props="props" key="antivirus">
            <q-icon v-if="props.row.antivirus !== 'n/a' && props.row.antivirus === 'windowsdefender'" name="fas fa-exclamation" color="warning">
              <q-tooltip>{{ props.row.antivirus }}</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.antivirus !== 'n/a'" name="fas fa-check" color="positive">
              <q-tooltip>{{ props.row.antivirus }}</q-tooltip>
            </q-icon>
            <q-icon v-else name="fas fa-times-circle" color="negative" />
          </q-td>-->
          <q-td key="agentstatus">
            <q-icon
              v-if="props.row.status ==='overdue'"
              name="fas fa-signal"
              size="1.2em"
              color="negative"
            >
              <q-tooltip>Agent overdue</q-tooltip>
            </q-icon>
            <q-icon
              v-else-if="props.row.status ==='offline'"
              name="fas fa-signal"
              size="1.2em"
              color="warning"
            >
              <q-tooltip>Agent offline</q-tooltip>
            </q-icon>
            <q-icon v-else name="fas fa-signal" size="1.2em" color="positive">
              <q-tooltip>Agent online</q-tooltip>
            </q-icon>
          </q-td>
          <!-- needs reboot -->
          <q-td key="needsreboot">
            <q-icon v-if="props.row.needs_reboot" name="fas fa-power-off" color="primary">
              <q-tooltip>Reboot required</q-tooltip>
            </q-icon>
          </q-td>
          <q-td key="lastseen" :props="props">{{ props.row.last_seen }}</q-td>
          <q-td key="boottime" :props="props">{{ bootTime(props.row.boot_time) }}</q-td>
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
      <RebootLater @close="showRebootLaterModal = false" />
    </q-dialog>
    <!-- pending actions modal -->
    <PendingActions />
    <!-- add policy modal -->
    <q-dialog v-model="showPolicyAddModal">
      <PolicyAdd @close="showPolicyAddModal = false" type="agent" :pk="policyAddPk" />
    </q-dialog>
    <!-- send command modal -->
    <q-dialog v-model="showSendCommand">
      <SendCommand @close="showSendCommand = false" :pk="selectedAgentPk" />
    </q-dialog>
  </div>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
import { mapGetters } from "vuex";
import { openURL } from "quasar";
import EditAgent from "@/components/modals/agents/EditAgent";
import RebootLater from "@/components/modals/agents/RebootLater";
import PendingActions from "@/components/modals/logs/PendingActions";
import PolicyAdd from "@/components/automation/modals/PolicyAdd";
import SendCommand from "@/components/modals/agents/SendCommand";

export default {
  name: "AgentTable",
  props: ["frame", "columns", "tab", "filter", "userName"],
  components: {
    EditAgent,
    RebootLater,
    PendingActions,
    PolicyAdd,
    SendCommand
  },
  mixins: [mixins],
  data() {
    return {
      pagination: {
        rowsPerPage: 0,
        sortBy: "hostname",
        descending: false
      },
      showSendCommand: false,
      showEditAgentModal: false,
      showRebootLaterModal: false,
      showPolicyAddModal: false,
      policyAddPk: null
    };
  },
  methods: {
    rowDoubleClicked(pk) {
      this.$store.commit("setActiveRow", pk);
      this.$q.loading.show();
      // give time for store to change active row
      setTimeout(() => {
        this.$q.loading.hide();
        this.showEditAgentModal = true;
      }, 500);
    },
    runPatchStatusScan(pk, hostname) {
      axios.get(`/winupdate/${pk}/runupdatescan/`).then(r => {
        this.notifySuccess(`Scan will be run shortly on ${hostname}`);
      });
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
          this.notifyError(e.response.data, 5000);
        });
    },
    agentEdited() {
      this.$emit("refreshEdit");
    },
    showPendingActions(pk, hostname) {
      const data = { action: true, agentpk: pk, hostname: hostname };
      this.$store.commit("logs/TOGGLE_PENDING_ACTIONS", data);
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
      axios
        .get(`/checks/runchecks/${pk}/`)
        .then(r => this.notifySuccess(`Checks will now be re-run on ${r.data}`))
        .catch(e => this.notifyError("Something went wrong"));
    },
    removeAgent(pk, name) {
      this.$q
        .dialog({
          title: `Please type <code style="color:red">${name}</code> to confirm deletion.`,
          prompt: {
            model: "",
            type: "text",
            isValid: val => val === name
          },
          cancel: true,
          ok: { label: "Uninstall", color: "negative" },
          persistent: true,
          html: true
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
            .catch(() => this.notifyError("Something went wrong"));
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
                persistent: true
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
          this.notifyError("Something went wrong");
        });
    },
    rebootNow(pk, hostname) {
      this.$q
        .dialog({
          title: "Are you sure?",
          message: `Reboot ${hostname} now`,
          cancel: true,
          persistent: true
        })
        .onOk(() => {
          const data = { pk: pk, action: "rebootnow" };
          axios.post("/agents/poweraction/", data).then(r => {
            this.$q.dialog({
              title: `Restarting ${hostname}`,
              message: `${hostname} will now be restarted`
            });
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
    },
    overdueAlert(category, pk, alert_action) {
      const action = alert_action ? "enabled" : "disabled";
      const data = {
        pk: pk,
        alertType: category,
        action: action
      };
      const alertColor = alert_action ? "positive" : "warning";
      axios
        .post("/agents/overdueaction/", data)
        .then(r => {
          this.$q.notify({
            color: alertColor,
            icon: "fas fa-check-circle",
            message: `Overdue ${category} alerts ${action} on ${r.data}`
          });
        })
        .catch(e => this.notifyError(e.response.data.error));
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
    showPolicyAdd(pk) {
      this.policyAddPk = pk;
      this.showPolicyAddModal = true;
    },
    webRDP(pk) {
      this.$q.loading.show();
      this.$axios
        .get(`/agents/${pk}/meshcentral/`)
        .then(r => {
          this.$q.loading.hide();
          openURL(r.data.webrdp);
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data);
        });
    }
  },
  computed: {
    ...mapGetters(["selectedAgentPk"]),
    selectedRow() {
      return this.$store.state.selectedRow;
    },
    agentTableLoading() {
      return this.$store.state.agentTableLoading;
    }
  }
};
</script>

