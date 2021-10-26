<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card style="min-width: 60vw; height: 75vh">
      <q-bar>
        <q-btn @click="getRoles" class="q-mr-sm" dense flat icon="refresh" />
        <q-space />Manage Roles
        <q-space />
        <q-btn dense flat icon="close" v-close-popup />
      </q-bar>
      <q-table
        dense
        :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
        class="tabs-tbl-sticky"
        style="max-height: 70vh"
        binary-state-sort
        virtual-scroll
        :rows="roles"
        :columns="columns"
        row-key="id"
        :pagination="{ rowsPerPage: 0, sortBy: 'name', descending: false }"
        no-data-label="No Roles"
        :rows-per-page-options="[0]"
      >
        <template v-slot:top>
          <q-btn flat dense icon="add" label="New Role" @click="showAddRoleModal" />
        </template>
        <template v-slot:body="props">
          <q-tr :props="props" @dblclick="showEditRoleModal(props.row)" class="cursor-pointer">
            <q-menu context-menu auto-close>
              <q-list dense style="min-width: 200px">
                <q-item clickable @click="showEditRoleModal(props.row)">
                  <q-item-section side>
                    <q-icon name="edit" />
                  </q-item-section>
                  <q-item-section>Edit</q-item-section>
                </q-item>
                <q-item clickable @click="deleteRole(props.row)" :disable="props.row.user_count > 0">
                  <q-item-section side>
                    <q-icon name="delete" />
                  </q-item-section>
                  <q-item-section>Delete</q-item-section>
                </q-item>

                <q-separator></q-separator>

                <q-item clickable>
                  <q-item-section>Close</q-item-section>
                </q-item>
              </q-list>
            </q-menu>
            <q-td key="name" :props="props">{{ props.row.name }}</q-td>
            <q-td key="is_superuser" :props="props">
              <q-icon v-if="props.row.is_superuser" name="done" color="primary" size="sm" />
            </q-td>
            <q-td key="user_count" :props="props">
              {{ props.row.user_count }}
            </q-td>
          </q-tr>
        </template>
      </q-table>
    </q-card>
  </q-dialog>
</template>

<script>
// composition imports
import { ref, onMounted } from "vue";
import { useQuasar, useDialogPluginComponent } from "quasar";
import { fetchRoles, removeRole } from "@/api/accounts";
import { notifySuccess } from "@/utils/notify";

// ui imports
import RolesForm from "@/components/accounts/RolesForm";

// static data
const columns = [
  { name: "name", label: "Name", field: "name", align: "left", sortable: true },
  { name: "is_superuser", label: "Superuser", field: "is_superuser", align: "left", sortable: true },
  { name: "user_count", label: "Assigned Users", field: "user_count", align: "left", sortable: true },
];

export default {
  name: "PermissionsManager",
  emits: [...useDialogPluginComponent.emits],
  setup(props) {
    // setup quasar
    const $q = useQuasar();
    const { dialogRef, onDialogHide } = useDialogPluginComponent();

    // permission manager logic
    const roles = ref([]);
    const loading = ref(false);

    function showEditRoleModal(role) {
      $q.dialog({
        component: RolesForm,
        componentProps: {
          role: role,
        },
      }).onOk(getRoles);
    }

    function showAddRoleModal() {
      $q.dialog({
        component: RolesForm,
      }).onOk(getRoles);
    }

    async function getRoles() {
      loading.value = true;
      roles.value = await fetchRoles();
      loading.value = false;
    }

    async function deleteRole(role) {
      $q.dialog({
        title: `Delete role ${role.name}?`,
        cancel: true,
        ok: { label: "Delete", color: "negative" },
      }).onOk(async () => {
        try {
          $q.loading.show();
          const result = await removeRole(role.id);
          notifySuccess(result);
          await getRoles();
        } catch (e) {
          console.error(e);
        }
        $q.loading.hide();
      });
    }

    // vue lifecycle hooks
    onMounted(getRoles);

    return {
      // reactive data
      roles,
      loading,

      // non-reactive data
      columns,

      // methods
      getRoles,
      deleteRole,
      showAddRoleModal,
      showEditRoleModal,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>