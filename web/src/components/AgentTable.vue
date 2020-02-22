<template>
  <div class="q-pa-sm">
    <q-table 
      dense 
      class="agents-tbl-sticky" 
      :data="filter" 
      :columns="columns" 
      row-key="id" 
      binary-state-sort 
      :pagination.sync="pagination" 
      hide-bottom
    > 
      <!-- header slots -->
      <template v-slot:header-cell-smsalert="props">
        <q-th auto-width :props="props">
          <q-icon name="phone_android" size="1.5em"><q-tooltip>SMS Alert</q-tooltip></q-icon>
        </q-th>
      </template>
      <template v-slot:header-cell-emailalert="props">
        <q-th auto-width :props="props">
          <q-icon name="email" size="1.5em"><q-tooltip>Email Alert</q-tooltip></q-icon>
        </q-th>
      </template>
      <template v-slot:header-cell-patchespending="props">
        <q-th auto-width :props="props">
          <q-icon name="system_update_alt" size="1.5em" color="warning"><q-tooltip>Patches Pending</q-tooltip></q-icon>
        </q-th>
      </template>
      <!--
      <template v-slot:header-cell-antivirus="props">
        <q-th auto-width :props="props">
          <q-icon name="fas fa-shield-alt" size="1.2em" color="primary"><q-tooltip>Anti Virus</q-tooltip></q-icon>
        </q-th>
      </template> -->
      <template v-slot:header-cell-agentstatus="props">
        <q-th auto-width :props="props">
          <q-icon name="fas fa-signal" size="1.2em" color="accent"><q-tooltip>Agent Status</q-tooltip></q-icon>
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
              <q-item clickable v-close-popup>
                <q-item-section>Open...</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="showEditAgentModal = true">
                <q-item-section avatar>
                  <q-icon style="font-size: 0.9rem;" name="edit" />
                </q-item-section>
                <q-item-section>Edit {{ props.row.hostname }}</q-item-section>
              </q-item>

              <!-- take control -->
              <q-item
                clickable
                v-ripple
                v-close-popup
                @click.stop.prevent="takeControl(props.row.id)"
              >
                <q-item-section avatar>
                  <q-icon style="font-size: 0.8rem;" name="fas fa-desktop" />
                </q-item-section>

                <q-item-section>Take Control</q-item-section>
              </q-item>

              <q-item
                clickable
                v-ripple
                v-close-popup
                @click="toggleSendCommand(props.row.id, props.row.hostname)"
              >
                <q-item-section avatar>
                  <q-icon style="font-size: 0.8rem;" name="fas fa-terminal" />
                </q-item-section>
                <q-item-section>Send Command</q-item-section>
              </q-item>

              <q-separator />
              <q-item clickable v-close-popup @click.stop.prevent="remoteBG(props.row.id)">
                <q-item-section class="remote-bg" side></q-item-section>
                <q-item-section>Remote Background</q-item-section>
              </q-item>
              
              <!-- patch management -->
              <q-separator />
              <q-item clickable>
                <q-item-section side>
                  <q-icon name="power_settings_new" />
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
                  </q-list>
                </q-menu>

              </q-item>

              <q-separator />
              <q-item clickable>
                <q-item-section side>
                  <q-icon name="power_settings_new" />
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
                      @click.stop.prevent="rebootLater(props.row.id, props.row.hostname)"
                    >
                      <q-item-section>Later</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
              </q-item>

              <q-separator />
              <q-item clickable v-close-popup @click.stop.prevent="removeAgent(props.row.id, props.row.hostname)">
                <q-item-section side><q-icon name="delete" /></q-item-section>
                <q-item-section>Remove Agent</q-item-section>
              </q-item>

              <q-separator />
              <q-item clickable v-close-popup>
                <q-item-section>Quit</q-item-section>
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
          <q-td key="platform" :props="props">
            <q-icon v-if="props.row.plat === 'windows'" name="fab fa-windows" color="blue" />
            <q-icon v-else-if="props.row.plat === 'linux'" name="fab fa-linux" color="blue" />
          </q-td>
          <q-td key="client" :props="props">{{ props.row.client }}</q-td>
          <q-td key="site" :props="props">{{ props.row.site }}</q-td>

          <q-td key="hostname" :props="props">{{ props.row.hostname }}</q-td>
          <q-td key="description" :props="props">{{ props.row.description }}</q-td>
          <q-td :props="props" key="patchespending">
            <q-icon v-if="props.row.patches_pending" name="fas fa-power-off" color="primary">
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
          </q-td> -->
          <q-td key="agentstatus">
            <q-icon v-if="props.row.status ==='overdue'" name="fas fa-exclamation-triangle" color="negative">
              <q-tooltip>Agent overdue</q-tooltip>
            </q-icon>
            <q-icon v-else-if="props.row.status ==='offline'" name="fas fa-exclamation-triangle" color="grey-8">
              <q-tooltip>Agent offline</q-tooltip>
            </q-icon>
            <q-icon v-else name="fas fa-check" color="positive">
              <q-tooltip>Agent online</q-tooltip>
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
    <!-- send command modal -->
    <q-dialog v-model="sendCommandToggle" persistent>
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Send cmd on {{ sendCommandHostname }}</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit.prevent="sendCommand">
            <q-card-section>
              <q-input
                dense
                v-model="rawCMD"
                persistent
                autofocus
                :rules="[val => !!val || 'Field is required']"
              />
            </q-card-section>
            <q-card-actions align="right" class="text-primary">
              <q-btn flat color="red" label="Cancel" v-close-popup />
              <q-btn color="positive" :loading="loadingSendCMD" label="Send" type="submit" />
            </q-card-actions>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
    <!-- edit agent modal -->
    <q-dialog v-model="showEditAgentModal">
      <EditAgent @close="showEditAgentModal = false" @edited="agentEdited" />
    </q-dialog>
  </div>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
import EditAgent from "@/components/modals/agents/EditAgent";
export default {
  name: "AgentTable",
  props: ["frame", "columns", "tab", "filter", "userName"],
  components: {EditAgent},
  mixins: [mixins],
  data() {
    return {
      pagination: {
        rowsPerPage: 9999,
        sortBy: "hostname",
        descending: false
      },
      sendCommandToggle: false,
      sendCommandID: null,
      sendCommandHostname: "",
      rawCMD: "",
      loadingSendCMD: false,
      showEditAgentModal: false
    };
  },
  methods: {
    rowDoubleClicked(pk) {
      this.$store.commit("setActiveRow", pk);
      this.$q.loading.show();
      // give time for store to change active row
      setTimeout(()=>{
        this.$q.loading.hide();
        this.showEditAgentModal = true;
      }, 500);
    },
    runPatchStatusScan(pk, hostname) {
        axios.get(`/winupdate/${pk}/runupdatescan/`).then(r => {
            this.notifySuccess(`Scan will be run shortly on ${hostname}`)
        })
    },
    agentEdited() {
      this.$emit("refreshEdit")
    },
    takeControl(pk) {
      const url = this.$router.resolve(`/takecontrol/${pk}`).href;
      window.open(
        url,
        "",
        "scrollbars=no,location=no,status=no,toolbar=no,menubar=no,width=1600,height=900"
      );
    },
    remoteBG(pk) {
      const url = this.$router.resolve(`/remotebackground/${pk}`).href;
      window.open(
        url,
        "",
        "scrollbars=no,location=no,status=no,toolbar=no,menubar=no,width=1280,height=826"
      );
    },
    removeAgent(pk, hostname) {
      this.$q.dialog({
        title: "Are you sure?",
        message: `Delete agent ${hostname}`,
        cancel: true,
        persistent: true
      })
      .onOk(() => {
        this.$q.dialog({
          title: `Please type <code style="color:red">${hostname}</code> to confirm`,
          prompt: {model: '', type: 'text'},
          cancel: true,
          persistent: true,
          html: true
        }).onOk((hostnameConfirm) => {
          if (hostnameConfirm !== hostname) {
            this.$q.notify({
              message: "ERROR: Please type the correct hostname",
              color: "red"
            })
          } else {
            const data = {pk: pk};
            axios.delete("/agents/uninstallagent/", {data: data}).then(r => {
              this.$q.notify({
                message: `${hostname} will now be uninstalled!`,
                color: "green"
              })
            })
            .catch(e => {
              this.$q.notify({
                message: e.response.data.error,
                color: "info",
                timeout: 4000
              })
            })
          }
        })
      })
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
    rebootLater() {
      // TODO implement this
      console.log('reboot later')
    },
    toggleSendCommand(pk, hostname) {
      this.sendCommandToggle = true;
      this.sendCommandID = pk;
      this.sendCommandHostname = hostname;
    },
    sendCommand() {
      const rawcmd = this.rawCMD;
      const hostname = this.sendCommandHostname;
      const pk = this.sendCommandID;
      const data = {
        pk: pk,
        rawcmd: rawcmd
      };
      this.loadingSendCMD = true;
      axios
        .post("/agents/sendrawcmd/", data)
        .then(r => {
          this.loadingSendCMD = false;
          this.sendCommandToggle = false;
          this.$q.dialog({
            title: `<code>${rawcmd} on ${hostname}`,
            style: "width: 900px; max-width: 90vw",
            message: `<pre>${r.data}</pre>`,
            html: true
          });
        })
        .catch(err => {
          this.loadingSendCMD = false;
          this.$q.notify({
            color: "red",
            icon: "fas fa-times-circle",
            message: err.response.data
          });
        });
    },
    agentRowSelected(pk) {
      this.$store.commit("setActiveRow", pk);
      this.$store.dispatch("loadSummary", pk);
      this.$store.dispatch("loadChecks", pk);
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
        .catch(e => {
          console.log(e.response.data.error);
        });
    },
    agentClass(status) {
      if (status === 'offline') {
        return 'agent-offline'
      } else if (status === 'overdue') {
        return 'agent-overdue'
      } else {
        return 'agent-normal'
      }
    }
  },
  computed: {
    selectedRow() {
      return this.$store.state.selectedRow;
    },
    agentTableLoading() {
      return this.$store.state.agentTableLoading;
    }
  }
};
</script>

<style lang="stylus">
.agents-tbl-sticky {
  .q-table__middle {
    max-height: 35vh;
  }

  .q-table__top, .q-table__bottom, thead tr:first-child th {
    background-color: white;
  }

  thead tr:first-child th {
    position: sticky;
    top: 0;
    opacity: 1;
    z-index: 1;
  }
}

.highlight {
  background-color: #c9e6ff;
}
.remote-bg {
  background: url("../assets/remote-bg.png") no-repeat center;
  width: 16px;
  margin-right: 10px;
}
.agent-offline {
  background: gray !important
}
.agent-overdue {
  background: red !important
}
</style>

