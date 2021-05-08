<template>
  <q-card style="min-width: 85vh">
    <q-splitter v-model="splitterModel">
      <template v-slot:before>
        <q-tabs dense v-model="tab" vertical class="text-primary">
          <q-tab name="detail" label="Details" />
          <q-tab name="perms" label="Permissions" />
        </q-tabs>
      </template>
      <template v-slot:after>
        <q-form ref="form" @submit="onSubmit">
          <q-card-section class="row items-center">
            <div class="text-h6">{{ title }}</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </q-card-section>
          <q-scroll-area style="height: 65vh">
            <q-tab-panels v-model="tab" animated transition-prev="jump-up" transition-next="jump-up">
              <!-- Details -->
              <q-tab-panel name="detail">
                <q-card-section class="row">
                  <div class="col-2">Username:</div>
                  <div class="col-10">
                    <q-input
                      outlined
                      dense
                      v-model="settings.username"
                      :rules="[val => !!val || '*Required']"
                      class="q-pa-none"
                    />
                  </div>
                </q-card-section>
                <q-card-section class="row" v-if="!pk">
                  <div class="col-2">Password:</div>
                  <div class="col-10">
                    <q-input
                      outlined
                      dense
                      v-model="settings.password"
                      :type="isPwd ? 'password' : 'text'"
                      :rules="[val => !!val || '*Required']"
                      class="q-pa-none"
                    >
                      <template v-slot:append>
                        <q-icon
                          :name="isPwd ? 'visibility_off' : 'visibility'"
                          class="cursor-pointer"
                          @click="isPwd = !isPwd"
                        />
                      </template>
                    </q-input>
                  </div>
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">Email:</div>
                  <div class="col-10">
                    <q-input
                      outlined
                      dense
                      v-model="settings.email"
                      :rules="[val => isValidEmail(val) || 'Invalid email']"
                      class="q-pa-none"
                    />
                  </div>
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">First Name:</div>
                  <div class="col-10">
                    <q-input outlined dense v-model="settings.first_name" />
                  </div>
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">Last Name:</div>
                  <div class="col-10">
                    <q-input outlined dense v-model="settings.last_name" />
                  </div>
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">Active:</div>
                  <div class="col-10">
                    <q-toggle
                      v-model="settings.is_active"
                      color="green"
                      :disable="settings.username === logged_in_user"
                    />
                  </div>
                </q-card-section>
              </q-tab-panel>
              <!-- Permissions -->
              <q-tab-panel name="perms">
                <div class="text-subtitle2">Super User</div>
                <hr />
                <q-card-section class="row">
                  <div class="q-gutter-sm">
                    <q-checkbox v-model="settings.is_superuser" label="Super User" @input="superUser" />
                  </div>
                </q-card-section>

                <div class="text-subtitle2">Accounts</div>
                <hr />
                <q-card-section class="row">
                  <div class="q-gutter-sm">
                    <q-checkbox v-model="settings.can_manage_accounts" label="Manage User Accounts" />
                  </div>
                </q-card-section>

                <div class="text-subtitle2">Agents</div>
                <hr />
                <q-card-section class="row">
                  <div class="q-gutter-sm">
                    <q-checkbox v-model="settings.can_use_mesh" label="Use MeshCentral" />
                    <q-checkbox v-model="settings.can_uninstall_agents" label="Uninstall Agents" />
                    <q-checkbox v-model="settings.can_update_agents" label="Update Agents" />
                    <q-checkbox v-model="settings.can_edit_agent" label="Edit Agents" />
                    <q-checkbox v-model="settings.can_manage_procs" label="Manage Processes" />
                    <q-checkbox v-model="settings.can_view_eventlogs" label="View Event Logs" />
                    <q-checkbox v-model="settings.can_send_cmd" label="Send Command" />
                    <q-checkbox v-model="settings.can_reboot_agents" label="Reboot Agents" />
                    <q-checkbox v-model="settings.can_install_agents" label="Install Agents" />
                    <q-checkbox v-model="settings.can_run_scripts" label="Run Script" />
                    <q-checkbox v-model="settings.can_run_bulk" label="Bulk Actions" />
                  </div>
                </q-card-section>
                <div class="text-subtitle2">Core</div>
                <hr />
                <q-card-section class="row">
                  <div class="q-gutter-sm">
                    <q-checkbox v-model="settings.can_manage_notes" label="Manage Notes" />
                    <q-checkbox v-model="settings.can_edit_core_settings" label="Edit Global Settings" />
                    <q-checkbox v-model="settings.can_do_server_maint" label="Do Server Maintenance" />
                    <q-checkbox v-model="settings.can_code_sign" label="Manage Code Signing" />
                  </div>
                </q-card-section>

                <div class="text-subtitle2">Checks</div>
                <hr />
                <q-card-section class="row">
                  <div class="q-gutter-sm">
                    <q-checkbox v-model="settings.can_manage_checks" label="Manage Checks" />
                    <q-checkbox v-model="settings.can_run_checks" label="Run Checks" />
                  </div>
                </q-card-section>

                <div class="text-subtitle2">Clients</div>
                <hr />
                <q-card-section class="row">
                  <div class="q-gutter-sm">
                    <q-checkbox v-model="settings.can_manage_clients" label="Manage Clients" />
                    <q-checkbox v-model="settings.can_manage_sites" label="Manage Sites" />
                    <q-checkbox v-model="settings.can_manage_deployments" label="Manage Deployments" />
                  </div>
                </q-card-section>

                <div class="text-subtitle2">Automation Policies</div>
                <hr />
                <q-card-section class="row">
                  <div class="q-gutter-sm">
                    <q-checkbox v-model="settings.can_manage_automation_policies" label="Manage Automation Policies" />
                  </div>
                </q-card-section>

                <div class="text-subtitle2">Tasks</div>
                <hr />
                <q-card-section class="row">
                  <div class="q-gutter-sm">
                    <q-checkbox v-model="settings.can_manage_autotasks" label="Manage Tasks" />
                    <q-checkbox v-model="settings.can_run_autotasks" label="Run Tasks" />
                  </div>
                </q-card-section>

                <div class="text-subtitle2">Logs</div>
                <hr />
                <q-card-section class="row">
                  <div class="q-gutter-sm">
                    <q-checkbox v-model="settings.can_view_auditlogs" label="View Audit Logs" />
                    <q-checkbox v-model="settings.can_manage_pendingactions" label="Manage Pending Actions" />
                    <q-checkbox v-model="settings.can_view_debuglogs" label="View Debug Logs" />
                  </div>
                </q-card-section>

                <div class="text-subtitle2">Scripts</div>
                <hr />
                <q-card-section class="row">
                  <div class="q-gutter-sm">
                    <q-checkbox v-model="settings.can_manage_scripts" label="Manage Scripts" />
                  </div>
                </q-card-section>

                <div class="text-subtitle2">Alerts</div>
                <hr />
                <q-card-section class="row">
                  <div class="q-gutter-sm">
                    <q-checkbox v-model="settings.can_manage_alerts" label="Manage Alerts" />
                  </div>
                </q-card-section>

                <div class="text-subtitle2">Windows Services</div>
                <hr />
                <q-card-section class="row">
                  <div class="q-gutter-sm">
                    <q-checkbox v-model="settings.can_manage_winsvcs" label="Manage Windows Services" />
                  </div>
                </q-card-section>

                <div class="text-subtitle2">Software</div>
                <hr />
                <q-card-section class="row">
                  <div class="q-gutter-sm">
                    <q-checkbox v-model="settings.can_manage_software" label="Manage Software" />
                  </div>
                </q-card-section>

                <div class="text-subtitle2">Windows Updates</div>
                <hr />
                <q-card-section class="row">
                  <div class="q-gutter-sm">
                    <q-checkbox v-model="settings.can_manage_winupdates" label="Manage Windows Updates" />
                  </div>
                </q-card-section>
              </q-tab-panel>
            </q-tab-panels>
          </q-scroll-area>
          <q-card-section class="row items-center">
            <q-btn :disable="!disableSave" label="Save" color="primary" type="submit" />
          </q-card-section>
        </q-form>
      </template>
    </q-splitter>
  </q-card>
</template>

<script>
import { mapState } from "vuex";
import mixins from "@/mixins/mixins";

export default {
  name: "UserForm",
  mixins: [mixins],
  props: { pk: Number },
  data() {
    return {
      settings: {
        username: "",
        password: "",
        email: "",
        first_name: "",
        last_name: "",
        is_superuser: false,
        is_active: true,
        can_use_mesh: false,
        can_uninstall_agents: false,
        can_update_agents: false,
        can_edit_agent: false,
        can_manage_procs: false,
        can_view_eventlogs: false,
        can_send_cmd: false,
        can_reboot_agents: false,
        can_install_agents: false,
        can_run_scripts: false,
        can_run_bulk: false,
        can_manage_notes: false,
        can_edit_core_settings: false,
        can_do_server_maint: false,
        can_code_sign: false,
        can_manage_checks: false,
        can_run_checks: false,
        can_manage_clients: false,
        can_manage_sites: false,
        can_manage_deployments: false,
        can_manage_automation_policies: false,
        can_manage_autotasks: false,
        can_run_autotasks: false,
        can_view_auditlogs: false,
        can_manage_pendingactions: false,
        can_view_debuglogs: false,
        can_manage_scripts: false,
        can_manage_alerts: false,
        can_manage_winsvcs: false,
        can_manage_software: false,
        can_manage_winupdates: false,
        can_manage_accounts: false,
      },
      isPwd: true,
      splitterModel: 15,
      tab: "detail",
    };
  },
  computed: {
    disableSave() {
      if (this.pk) {
        return !!this.settings.username;
      } else {
        return !!this.settings.username && !!this.settings.password;
      }
    },
    title() {
      return this.pk ? "Edit User" : "Add User";
    },
    ...mapState({
      logged_in_user: state => state.username,
    }),
  },
  methods: {
    getUser() {
      this.$q.loading.show();
      this.$store.dispatch("admin/loadUser", this.pk).then(r => {
        this.$q.loading.hide();
        this.settings = r.data;
      });
    },
    getPerms() {
      this.$axios.get("/accounts/users/").then(r => (this.settings.perms = r.data[0].perms));
    },
    superUser(val) {
      for (const prop in this.settings) {
        if (this.settings.perms.indexOf(`${prop}`) > -1) {
          this.settings[prop] = val;
        }
      }
    },
    onSubmit() {
      this.$q.loading.show();
      delete this.settings.last_login;

      if (this.pk) {
        // dont allow updating is_active if username is same as logged in user
        if (this.settings.username === this.logged_in_user) {
          delete this.settings.is_active;
        }

        this.$store
          .dispatch("admin/editUser", this.settings)
          .then(() => {
            this.$q.loading.hide();
            this.$emit("close");
            this.notifySuccess("User edited!");
          })
          .catch(() => {
            this.$q.loading.hide();
          });
      } else {
        this.$store
          .dispatch("admin/addUser", this.settings)
          .then(r => {
            this.$q.loading.hide();
            this.$emit("close");
            this.notifySuccess(`User ${r.data} was added!`);
          })
          .catch(() => {
            this.$q.loading.hide();
          });
      }
    },
  },
  mounted() {
    // If pk prop is set that means we are editting
    if (this.pk) {
      this.getUser();
    } else {
      this.getPerms();
    }
  },
};
</script>