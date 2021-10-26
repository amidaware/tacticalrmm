<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card style="min-width: 75vw; max-heigth: 75vh" class="q-dialog-plugin">
      <q-bar>
        {{ localRole ? "Editing Role" : "Adding Role" }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup />
      </q-bar>
      <q-form ref="form" @submit="onSubmit">
        <q-card-section class="row">
          <q-input
            label="Role Name"
            class="col-6"
            dense
            outlined
            v-model="localRole.name"
            :rules="[val => !!val || '*Required']"
          />
        </q-card-section>
        <q-card-section class="scroll" style="height: 70vh">
          <!-- Permissions -->
          <div class="text-subtitle2">Super User</div>
          <hr />
          <q-card-section class="row">
            <div class="q-gutter-sm">
              <q-checkbox v-model="localRole.is_superuser" label="Super User" />
            </div>
          </q-card-section>

          <div class="text-subtitle2">Accounts</div>
          <hr />
          <q-card-section class="row">
            <div class="q-gutter-sm">
              <q-checkbox v-model="localRole.can_list_accounts" label="List User Accounts" />
              <q-checkbox v-model="localRole.can_manage_accounts" label="Manage User Accounts" />
              <q-checkbox v-model="localRole.can_list_roles" label="List Roles" />
              <q-checkbox v-model="localRole.can_manage_roles" label="Manage Roles" />
            </div>
          </q-card-section>

          <div class="text-subtitle2">Agents</div>
          <hr />
          <q-card-section class="row">
            <div class="q-gutter-sm">
              <q-checkbox v-model="localRole.can_list_agents" label="List Agents" />
              <q-checkbox v-model="localRole.can_list_agent_history" label="List Agent History" />
              <q-checkbox v-model="localRole.can_use_mesh" label="Use MeshCentral" />
              <q-checkbox v-model="localRole.can_uninstall_agents" label="Uninstall Agents" />
              <q-checkbox v-model="localRole.can_ping_agents" label="Ping Agents" />
              <q-checkbox v-model="localRole.can_update_agents" label="Update Agents" />
              <q-checkbox v-model="localRole.can_edit_agent" label="Edit Agents" />
              <q-checkbox v-model="localRole.can_manage_procs" label="Manage Processes" />
              <q-checkbox v-model="localRole.can_view_eventlogs" label="View Event Logs" />
              <q-checkbox v-model="localRole.can_send_cmd" label="Send Command" />
              <q-checkbox v-model="localRole.can_reboot_agents" label="Reboot Agents" />
              <q-checkbox v-model="localRole.can_install_agents" label="Install Agents" />
              <q-checkbox v-model="localRole.can_run_scripts" label="Run Script" />
              <q-checkbox v-model="localRole.can_run_bulk" label="Bulk Actions" />
              <q-checkbox v-model="localRole.can_recover_agents" label="Recover Agents" />
            </div>
          </q-card-section>
          <div class="text-subtitle2">Core</div>
          <hr />
          <q-card-section class="row">
            <div class="q-gutter-sm">
              <q-checkbox v-model="localRole.can_list_notes" label="List Notes" />
              <q-checkbox v-model="localRole.can_manage_notes" label="Manage Notes" />
              <q-checkbox v-model="localRole.can_view_core_settings" label="View Global Settings" />
              <q-checkbox v-model="localRole.can_edit_core_settings" label="Edit Global Settings" />
              <q-checkbox v-model="localRole.can_do_server_maint" label="Do Server Maintenance" />
              <q-checkbox v-model="localRole.can_code_sign" label="Manage Code Signing" />
              <q-checkbox v-model="localRole.can_list_api_keys" label="List API Keys" />
              <q-checkbox v-model="localRole.can_manage_api_keys" label="Manage API Keys" />
              <q-checkbox v-model="localRole.can_run_urlactions" label="Run URL Actions" />
            </div>
          </q-card-section>

          <div class="text-subtitle2">Checks</div>
          <hr />
          <q-card-section class="row">
            <div class="q-gutter-sm">
              <q-checkbox v-model="localRole.can_list_checks" label="List Checks" />
              <q-checkbox v-model="localRole.can_manage_checks" label="Manage Checks" />
              <q-checkbox v-model="localRole.can_run_checks" label="Run Checks" />
            </div>
          </q-card-section>

          <div class="text-subtitle2">Clients</div>
          <hr />
          <q-card-section class="row">
            <div class="q-gutter-sm">
              <q-checkbox v-model="localRole.can_list_clients" label="List Clients" />
              <q-checkbox v-model="localRole.can_manage_clients" label="Manage Clients" />
              <q-checkbox v-model="localRole.can_list_sites" label="List Sites" />
              <q-checkbox v-model="localRole.can_manage_sites" label="Manage Sites" />
              <q-checkbox v-model="localRole.can_list_deployments" label="List Deployments" />
              <q-checkbox v-model="localRole.can_manage_deployments" label="Manage Deployments" />
            </div>
          </q-card-section>

          <q-card-section class="row">
            <tactical-dropdown
              class="col-6"
              label="Allowed Clients"
              :options="clientOptions"
              v-model="localRole.can_view_clients"
              hint="Empty means all clients are allowed"
              outlined
              mapOptions
              multiple
            />
          </q-card-section>
          <q-card-section class="row">
            <tactical-dropdown
              class="col-6"
              label="Allowed Sites"
              :options="siteOptions"
              v-model="localRole.can_view_sites"
              hint="Empty means all sites are allowed"
              outlined
              mapOptions
              multiple
            />
          </q-card-section>

          <div class="text-subtitle2">Automation Policies</div>
          <hr />
          <q-card-section class="row">
            <div class="q-gutter-sm">
              <q-checkbox v-model="localRole.can_list_automation_policies" label="List Automation Policies" />
              <q-checkbox v-model="localRole.can_manage_automation_policies" label="Manage Automation Policies" />
            </div>
          </q-card-section>

          <div class="text-subtitle2">Tasks</div>
          <hr />
          <q-card-section class="row">
            <div class="q-gutter-sm">
              <q-checkbox v-model="localRole.can_list_autotasks" label="List Tasks" />
              <q-checkbox v-model="localRole.can_manage_autotasks" label="Manage Tasks" />
              <q-checkbox v-model="localRole.can_run_autotasks" label="Run Tasks" />
            </div>
          </q-card-section>

          <div class="text-subtitle2">Logs</div>
          <hr />
          <q-card-section class="row">
            <div class="q-gutter-sm">
              <q-checkbox v-model="localRole.can_view_auditlogs" label="View Audit Logs" />
              <q-checkbox v-model="localRole.can_view_debuglogs" label="View Debug Logs" />
              <q-checkbox v-model="localRole.can_list_pendingactions" label="List Pending Actions" />
              <q-checkbox v-model="localRole.can_manage_pendingactions" label="Manage Pending Actions" />
            </div>
          </q-card-section>

          <div class="text-subtitle2">Scripts</div>
          <hr />
          <q-card-section class="row">
            <div class="q-gutter-sm">
              <q-checkbox v-model="localRole.can_list_scripts" label="List Scripts" />
              <q-checkbox v-model="localRole.can_manage_scripts" label="Manage Scripts" />
            </div>
          </q-card-section>

          <div class="text-subtitle2">Alerts</div>
          <hr />
          <q-card-section class="row">
            <div class="q-gutter-sm">
              <q-checkbox v-model="localRole.can_list_alerts" label="List Alerts" />
              <q-checkbox v-model="localRole.can_manage_alerts" label="Manage Alerts" />
              <q-checkbox v-model="localRole.can_list_alerttemplates" label="List Alert Templates" />
              <q-checkbox v-model="localRole.can_manage_alerttemplates" label="Manage Alert Templates" />
            </div>
          </q-card-section>

          <div class="text-subtitle2">Windows Services</div>
          <hr />
          <q-card-section class="row">
            <div class="q-gutter-sm">
              <q-checkbox v-model="localRole.can_manage_winsvcs" label="Manage Windows Services" />
            </div>
          </q-card-section>

          <div class="text-subtitle2">Software</div>
          <hr />
          <q-card-section class="row">
            <div class="q-gutter-sm">
              <q-checkbox v-model="localRole.can_list_software" label="List Software" />
              <q-checkbox v-model="localRole.can_manage_software" label="Manage Software" />
            </div>
          </q-card-section>

          <div class="text-subtitle2">Windows Updates</div>
          <hr />
          <q-card-section class="row">
            <div class="q-gutter-sm">
              <q-checkbox v-model="localRole.can_manage_winupdates" label="Manage Windows Updates" />
            </div>
          </q-card-section>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn dense flat label="Cancel" v-close-popup />
          <q-btn :loading="loading" dense flat label="Save" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref, watch } from "vue";
import { useDialogPluginComponent } from "quasar";
import { saveRole, editRole } from "@/api/accounts";
import { useClientDropdown, useSiteDropdown } from "@/composables/clients";
import { notifySuccess } from "@/utils/notify";

// ui imports
import TacticalDropdown from "@/components/ui/TacticalDropdown.vue";

export default {
  components: { TacticalDropdown },
  name: "RolesForm",
  emits: [...useDialogPluginComponent.emits],
  props: { role: Object },
  setup(props) {
    // quasar setup
    const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();

    // dropdown setup
    const { clientOptions } = useClientDropdown(true);
    const { siteOptions } = useSiteDropdown(true);

    const role = props.role
      ? ref(Object.assign({}, props.role))
      : ref({
          name: "",
          is_superuser: false,
          // agent perms
          can_list_agents: false,
          can_recover_agents: false,
          can_use_mesh: false,
          can_uninstall_agents: false,
          can_update_agents: false,
          can_edit_agent: false,
          can_ping_agents: false,
          can_manage_procs: false,
          can_view_eventlogs: false,
          can_send_cmd: false,
          can_reboot_agents: false,
          can_install_agents: false,
          can_run_scripts: false,
          can_run_bulk: false,
          can_manage_winsvcs: false,
          can_recover_agents: false,
          can_list_agent_history: false,
          // software perms
          can_list_software: false,
          can_manage_software: false,
          // note perms
          can_list_notes: false,
          can_manage_notes: false,
          // settings perms
          can_view_core_settings: false,
          can_edit_core_settings: false,
          can_do_server_maint: false,
          can_code_sign: false,
          can_run_urlactions: false,
          // api key perms
          can_list_api_keys: false,
          can_manage_api_keys: false,
          // check perms
          can_list_checks: false,
          can_manage_checks: false,
          can_run_checks: false,
          // client perms
          can_list_clients: false,
          can_manage_clients: false,
          can_list_sites: false,
          can_manage_sites: false,
          // deployment perms
          can_list_deployments: false,
          can_manage_deployments: false,
          // automation perms
          can_list_automation_policies: false,
          can_manage_automation_policies: false,
          // task perms
          can_list_autotasks: false,
          can_manage_autotasks: false,
          can_run_autotasks: false,
          // log perms
          can_view_auditlogs: false,
          can_view_debuglogs: false,
          can_list_pendingactions: false,
          can_manage_pendingactions: false,
          // script perms
          can_list_scripts: false,
          can_manage_scripts: false,
          // alert perms
          can_list_alerts: false,
          can_manage_alerts: false,
          can_list_alerttemplates: false,
          can_manage_alerttemplates: false,
          // update perms
          can_manage_winupdates: false,
          // account perms
          can_list_accounts: false,
          can_manage_accounts: false,
          can_list_roles: false,
          can_manage_roles: false,
          can_view_clients: [],
          can_view_sites: [],
        });

    const loading = ref(false);

    async function onSubmit() {
      loading.value = true;
      try {
        const result = props.role ? await editRole(role.value.id, role.value) : await saveRole(role.value);
        notifySuccess(result);
        onDialogOK();
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    watch(
      () => role.value.is_superuser,
      (newValue, oldValue) => {
        Object.keys(role.value).forEach((key, index) => {
          if (typeof role.value[key] === "boolean") {
            role.value[key] = newValue;
          }
        });
      }
    );

    return {
      // reactive data
      localRole: role,
      loading,
      clientOptions,
      siteOptions,

      onSubmit,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>