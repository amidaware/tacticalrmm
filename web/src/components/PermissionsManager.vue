<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card style="min-width: 30vw">
      <q-bar>
        <q-btn @click="getRoles" class="q-mr-sm" dense flat push icon="refresh" />
        <q-space />Manage Roles
        <q-space />
        <q-btn dense flat icon="close" v-close-popup />
      </q-bar>
      <div class="row">
        <div class="q-pa-sm q-ml-sm">
          <q-btn color="primary" icon="add" label="New Role" @click="showRolesForm = true" />
        </div>
      </div>
      <q-separator />
      <q-card-section>
        <q-table
          dense
          :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
          class="audit-mgr-tbl-sticky"
          binary-state-sort
          virtual-scroll
          :rows="roles"
          :columns="columns"
          :visible-columns="visibleColumns"
          row-key="id"
          v-model:pagination="pagination"
          no-data-label="No Roles"
        >
          <template v-slot:body="props">
            <q-tr>
              <q-td key="name" :props="props">{{ props.row.name }}</q-td>
              <q-td class="q-pa-md q-gutter-sm" key="actions" :props="props"
                ><q-btn size="sm" color="primary" icon="edit" @click="editRole(props.row.id)" />
                <q-btn size="sm" color="negative" icon="delete" @click="deleteRole(props.row.id, props.row.name)"
              /></q-td>
            </q-tr>
          </template>
        </q-table>
      </q-card-section>

      <!-- Roles Form -->
      <q-dialog v-model="showRolesForm">
        <RolesForm :pk="editRoleID" @close="closeRoleFormModal" />
      </q-dialog>
    </q-card>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";
import RolesForm from "@/components/modals/admin/RolesForm";

export default {
  name: "PermissionsManager",
  emits: ["hide", "ok", "cancel"],
  mixins: [mixins],
  components: { RolesForm },
  data() {
    return {
      editRoleID: null,
      showRolesForm: false,
      roles: [],
      columns: [
        { name: "id", field: "id" },
        { name: "name", label: "Name", field: "name", align: "left", sortable: true },
        { name: "actions", label: "Actions", align: "left" },
      ],
      visibleColumns: ["name", "actions"],

      pagination: {
        rowsPerPage: 50,
        sortBy: "name",
        descending: false,
      },
    };
  },
  methods: {
    getRoles() {
      this.$axios
        .get("/accounts/roles/")
        .then(r => {
          this.roles = r.data;
        })
        .catch(() => {});
    },
    editRole(id) {
      this.editRoleID = id;
      this.showRolesForm = true;
    },
    deleteRole(pk, name) {
      this.$q
        .dialog({
          title: `Delete role ${name}?`,
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$axios
            .delete(`/accounts/${pk}/role/`)
            .then(() => {
              this.getRoles();
              this.notifySuccess(`Role ${name} was deleted!`);
            })
            .catch(() => {});
        });
    },
    closeRoleFormModal() {
      this.editRoleID = null;
      this.showRolesForm = false;
      this.getRoles();
    },
    show() {
      this.$refs.dialog.show();
    },
    hide() {
      this.$refs.dialog.hide();
    },
    onHide() {
      this.$emit("hide");
    },
  },
  created() {
    this.getRoles();
  },
};
</script>