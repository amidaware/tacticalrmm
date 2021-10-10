<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card style="min-width: 60vw">
      <q-bar>
        <q-btn @click="getRoles" class="q-mr-sm" dense flat push icon="refresh" />
        <q-space />Manage Roles
        <q-space />
        <q-btn dense flat icon="close" v-close-popup />
      </q-bar>
      <q-card-section>
        <q-table
          dense
          :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
          class="tabs-tbl-sticky"
          binary-state-sort
          virtual-scroll
          :rows="roles"
          :columns="columns"
          row-key="id"
          v-model:pagination="pagination"
          no-data-label="No Roles"
          hide-bottom
        >
          <template v-slot:top-left="props">
            <q-btn color="primary" icon="add" label="New Role" @click="showAddRoleModal" />
          </template>
          <template v-slot:body="props">
            <q-tr>
              <q-menu context-menu>
                <q-list dense style="min-width: 200px">
                  <q-item clickable v-close-popup @click="showEditRoleModal(props.row)">
                    <q-item-section side>
                      <q-icon name="edit" />
                    </q-item-section>
                    <q-item-section>Edit</q-item-section>
                  </q-item>
                  <q-item clickable v-close-popup @click="deleteRole(props.row)" :disable="props.row.user_count > 0">
                    <q-item-section side>
                      <q-icon name="delete" />
                    </q-item-section>
                    <q-item-section>Delete</q-item-section>
                  </q-item>

                  <q-separator></q-separator>

                  <q-item clickable v-close-popup>
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
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script>
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
    const roles = ref([]);
    const pagination = ref({
      rowsPerPage: 50,
      sortBy: "name",
      descending: false,
    });
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
      pagination,
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