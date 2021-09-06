<template>
  <q-card style="min-width: 85vh" class="q-pa-md">
    <q-form ref="form" @submit="onSubmit">
      <q-card-section class="row items-center">
        <div class="text-h6">{{ title }}</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Name:</div>
        <q-input dense outlined v-model="role.name" class="col-8" :rules="[val => !!val || '*Required']" />
        <div class="col-2"></div>
      </q-card-section>
      <q-card-section class="scroll" style="height: 75vh">
        <!-- Permissions -->
        <div class="text-subtitle2">Super User</div>
        <hr />
        <q-card-section class="row">
          <div class="q-gutter-sm">
            <q-checkbox v-model="role.is_superuser" label="Super User" @update:model-value="superUser" />
          </div>
        </q-card-section>

        <div class="text-subtitle2">Accounts</div>
        <hr />
        <q-card-section class="row">
          <div class="q-gutter-sm">
            <q-checkbox v-model="role.can_manage_accounts" label="Manage User Accounts" />
            <q-checkbox v-model="role.can_manage_roles" label="Manage Permissions" />
          </div>
        </q-card-section>

        <div class="text-subtitle2">Agents</div>
        <hr />
        <q-card-section class="row">
          <div class="q-gutter-sm">
            <q-checkbox v-model="role.can_use_mesh" label="Use MeshCentral" />
            <q-checkbox v-model="role.can_uninstall_agents" label="Uninstall Agents" />
            <q-checkbox v-model="role.can_update_agents" label="Update Agents" />
            <q-checkbox v-model="role.can_edit_agent" label="Edit Agents" />
            <q-checkbox v-model="role.can_manage_procs" label="Manage Processes" />
            <q-checkbox v-model="role.can_view_eventlogs" label="View Event Logs" />
            <q-checkbox v-model="role.can_send_cmd" label="Send Command" />
            <q-checkbox v-model="role.can_reboot_agents" label="Reboot Agents" />
            <q-checkbox v-model="role.can_install_agents" label="Install Agents" />
            <q-checkbox v-model="role.can_run_scripts" label="Run Script" />
            <q-checkbox v-model="role.can_run_bulk" label="Bulk Actions" />
          </div>
        </q-card-section>
        <div class="text-subtitle2">Core</div>
        <hr />
        <q-card-section class="row">
          <div class="q-gutter-sm">
            <q-checkbox v-model="role.can_manage_notes" label="Manage Notes" />
            <q-checkbox v-model="role.can_view_core_settings" label="View Global Settings" />
            <q-checkbox v-model="role.can_edit_core_settings" label="Edit Global Settings" />
            <q-checkbox v-model="role.can_do_server_maint" label="Do Server Maintenance" />
            <q-checkbox v-model="role.can_code_sign" label="Manage Code Signing" />
            <q-checkbox v-model="role.can_manage_api_keys" label="Manage API Keys" />
          </div>
        </q-card-section>

        <div class="text-subtitle2">Checks</div>
        <hr />
        <q-card-section class="row">
          <div class="q-gutter-sm">
            <q-checkbox v-model="role.can_manage_checks" label="Manage Checks" />
            <q-checkbox v-model="role.can_run_checks" label="Run Checks" />
          </div>
        </q-card-section>

        <div class="text-subtitle2">Clients</div>
        <hr />
        <q-card-section class="row">
          <div class="q-gutter-sm">
            <q-checkbox v-model="role.can_manage_clients" label="Manage Clients" />
            <q-checkbox v-model="role.can_manage_sites" label="Manage Sites" />
            <q-checkbox v-model="role.can_manage_deployments" label="Manage Deployments" />
          </div>
        </q-card-section>

        <div class="text-subtitle2">Automation Policies</div>
        <hr />
        <q-card-section class="row">
          <div class="q-gutter-sm">
            <q-checkbox v-model="role.can_manage_automation_policies" label="Manage Automation Policies" />
          </div>
        </q-card-section>

        <div class="text-subtitle2">Tasks</div>
        <hr />
        <q-card-section class="row">
          <div class="q-gutter-sm">
            <q-checkbox v-model="role.can_manage_autotasks" label="Manage Tasks" />
            <q-checkbox v-model="role.can_run_autotasks" label="Run Tasks" />
          </div>
        </q-card-section>

        <div class="text-subtitle2">Logs</div>
        <hr />
        <q-card-section class="row">
          <div class="q-gutter-sm">
            <q-checkbox v-model="role.can_view_auditlogs" label="View Audit Logs" />
            <q-checkbox v-model="role.can_manage_pendingactions" label="Manage Pending Actions" />
            <q-checkbox v-model="role.can_view_debuglogs" label="View Debug Logs" />
          </div>
        </q-card-section>

        <div class="text-subtitle2">Scripts</div>
        <hr />
        <q-card-section class="row">
          <div class="q-gutter-sm">
            <q-checkbox v-model="role.can_manage_scripts" label="Manage Scripts" />
          </div>
        </q-card-section>

        <div class="text-subtitle2">Alerts</div>
        <hr />
        <q-card-section class="row">
          <div class="q-gutter-sm">
            <q-checkbox v-model="role.can_manage_alerts" label="Manage Alerts" />
          </div>
        </q-card-section>

        <div class="text-subtitle2">Windows Services</div>
        <hr />
        <q-card-section class="row">
          <div class="q-gutter-sm">
            <q-checkbox v-model="role.can_manage_winsvcs" label="Manage Windows Services" />
          </div>
        </q-card-section>

        <div class="text-subtitle2">Software</div>
        <hr />
        <q-card-section class="row">
          <div class="q-gutter-sm">
            <q-checkbox v-model="role.can_manage_software" label="Manage Software" />
          </div>
        </q-card-section>

        <div class="text-subtitle2">Windows Updates</div>
        <hr />
        <q-card-section class="row">
          <div class="q-gutter-sm">
            <q-checkbox v-model="role.can_manage_winupdates" label="Manage Windows Updates" />
          </div>
        </q-card-section>
      </q-card-section>
      <q-card-section class="row items-center">
        <q-btn label="Save" color="primary" type="submit" />
      </q-card-section>
    </q-form>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "RolesForm",
  emits: ["close"],
  mixins: [mixins],
  props: { pk: Number },
  data() {
    return {
      roles: [],
      role: {
        name: "",
        is_superuser: false,
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
        can_view_core_settings: false,
        can_edit_core_settings: false,
        can_manage_api_keys: false,
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
        can_manage_roles: false,
      },
    };
  },
  computed: {
    title() {
      return this.pk ? "Edit Role" : "Add Role";
    },
  },
  methods: {
    getRole() {
      this.$q.loading.show();
      this.$axios.get(`/accounts/${this.pk}/role/`).then(r => {
        this.$q.loading.hide();
        this.role = r.data;
      });
    },
    getPerms() {
      this.$axios.get("/accounts/permslist/").then(r => (this.roles = r.data));
    },
    superUser(val) {
      for (const prop in this.role) {
        if (this.roles.indexOf(`${prop}`) > -1) {
          this.role[prop] = val;
        }
      }
    },
    onSubmit() {
      this.$q.loading.show();
      if (this.pk) {
        this.$axios
          .put(`/accounts/${this.pk}/role/`, this.role)
          .then(() => {
            this.$q.loading.hide();
            this.$emit("close");
            this.notifySuccess("Role edited!");
          })
          .catch(() => {
            this.$q.loading.hide();
          });
      } else {
        this.$axios
          .post("/accounts/roles/", this.role)
          .then(() => {
            this.$q.loading.hide();
            this.$emit("close");
            this.notifySuccess(`Role was added!`);
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
      this.getRole();
    }
    this.getPerms();
  },
};
</script>