<template>
  <div style="width: 900px; max-width: 90vw">
    <q-card>
      <q-bar>
        <q-btn ref="refresh" @click="refresh" class="q-mr-sm" dense flat push icon="refresh" />User Administration
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <div class="q-pa-md">
        <div class="q-gutter-sm">
          <q-btn ref="new" label="New" dense flat push unelevated no-caps icon="add" @click="showAddUserModal" />
        </div>
        <q-table
          dense
          :data="users"
          :columns="columns"
          :pagination.sync="pagination"
          :selected.sync="selected"
          selection="single"
          row-key="id"
          binary-state-sort
          hide-pagination
          :hide-bottom="!!selected"
        >
          <!-- header slots -->
          <template v-slot:header="props">
            <q-tr :props="props">
              <template v-for="col in props.cols">
                <q-th v-if="col.name === 'active'" auto-width :key="col.name">
                  <q-icon name="power_settings_new" size="1.5em">
                    <q-tooltip>Enable User</q-tooltip>
                  </q-icon>
                </q-th>

                <q-th v-else :key="col.name" :props="props">{{ col.label }}</q-th>
              </template>
            </q-tr>
          </template>
          <!-- No data Slot -->
          <template v-slot:no-data>
            <div class="full-width row flex-center q-gutter-sm">
              <span v-if="users.length === 0">No Users</span>
            </div>
          </template>
          <!-- body slots -->
          <template v-slot:body="props">
            <q-tr
              :props="props"
              class="cursor-pointer"
              :class="rowSelectedClass(props.row.id, selected)"
              @click="
                editUserId = props.row.id;
                props.selected = true;
              "
              @contextmenu="
                editUserId = props.row.id;
                props.selected = true;
              "
            >
              <!-- context menu -->
              <q-menu context-menu>
                <q-list dense style="min-width: 200px">
                  <q-item clickable v-close-popup @click="showEditUserModal(selected[0])" id="context-edit">
                    <q-item-section side>
                      <q-icon name="edit" />
                    </q-item-section>
                    <q-item-section>Edit</q-item-section>
                  </q-item>
                  <q-item
                    clickable
                    v-close-popup
                    @click="deleteUser(props.row)"
                    id="context-delete"
                    :disable="props.row.username === logged_in_user"
                  >
                    <q-item-section side>
                      <q-icon name="delete" />
                    </q-item-section>
                    <q-item-section>Delete</q-item-section>
                  </q-item>

                  <q-separator></q-separator>

                  <q-item clickable v-close-popup @click="ResetPassword(props.row)" id="context-reset">
                    <q-item-section side>
                      <q-icon name="autorenew" />
                    </q-item-section>
                    <q-item-section>Reset Password</q-item-section>
                  </q-item>

                  <q-item clickable v-close-popup @click="reset2FA(props.row)" id="context-reset">
                    <q-item-section side>
                      <q-icon name="autorenew" />
                    </q-item-section>
                    <q-item-section>Reset Two-Factor Auth</q-item-section>
                  </q-item>

                  <q-separator></q-separator>

                  <q-item clickable v-close-popup>
                    <q-item-section>Close</q-item-section>
                  </q-item>
                </q-list>
              </q-menu>
              <!-- enabled checkbox -->
              <q-td>
                <q-checkbox
                  dense
                  @input="toggleEnabled(props.row)"
                  v-model="props.row.is_active"
                  :disable="props.row.username === logged_in_user"
                />
              </q-td>
              <q-td>{{ props.row.username }}</q-td>
              <q-td>{{ props.row.first_name }} {{ props.row.last_name }}</q-td>
              <q-td>{{ props.row.email }}</q-td>
              <q-td v-if="props.row.last_login">{{ props.row.last_login }}</q-td>
              <q-td v-else>Never</q-td>
            </q-tr>
          </template>
        </q-table>
      </div>
    </q-card>

    <!-- user form modal -->
    <q-dialog v-model="showUserFormModal" @hide="closeUserFormModal">
      <UserForm :pk="editUserId" @close="closeUserFormModal" />
    </q-dialog>

    <!-- user reset password form modal -->
    <q-dialog v-model="showResetPasswordModal" @hide="closeResetPasswordModal">
      <UserResetPasswordForm :pk="resetUserId" :username="resetUserName" @close="closeResetPasswordModal" />
    </q-dialog>
  </div>
</template>

<script>
import mixins from "@/mixins/mixins";
import { mapState } from "vuex";
import UserForm from "@/components/modals/admin/UserForm";
import UserResetPasswordForm from "@/components/modals/admin/UserResetPasswordForm";

export default {
  name: "AdminManager",
  components: { UserForm, UserResetPasswordForm },
  mixins: [mixins],
  data() {
    return {
      showUserFormModal: false,
      showResetPasswordModal: false,
      editUserId: null,
      resetUserId: null,
      resetUserName: null,
      selected: [],
      columns: [
        { name: "is_active", label: "Active", field: "is_active", align: "left" },
        { name: "username", label: "Username", field: "username", align: "left" },
        {
          name: "name",
          label: "Name",
          field: "name",
          align: "left",
        },
        {
          name: "email",
          label: "Email",
          field: "email",
          align: "left",
        },
        {
          name: "last_login",
          label: "Last Login",
          field: "last_login",
          align: "left",
        },
      ],
      pagination: {
        rowsPerPage: 9999,
      },
    };
  },
  methods: {
    getUsers() {
      this.$store.dispatch("admin/loadUsers");
    },
    clearRow() {
      this.selected = [];
    },
    refresh() {
      this.getUsers();
      this.clearRow();
    },
    deleteUser(data) {
      this.$q
        .dialog({
          title: `Delete user ${data.username}?`,
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$store
            .dispatch("admin/deleteUser", data.id)
            .then(() => {
              this.notifySuccess(`User ${data.username} was deleted!`);
            })
            .catch(e => {});
        });
    },
    showEditUserModal(data) {
      this.editUserId = data.id;
      this.showUserFormModal = true;
    },
    closeUserFormModal() {
      this.showUserFormModal = false;
      this.editUserId = null;
      this.refresh();
    },
    showAddUserModal() {
      this.editUserId = null;
      this.selected = [];
      this.showUserFormModal = true;
    },
    toggleEnabled(user) {
      if (user.username === this.logged_in_user) {
        return;
      }
      let text = user.is_active ? "User enabled successfully" : "User disabled successfully";

      const data = {
        id: user.id,
        is_active: user.is_active,
      };

      this.$store
        .dispatch("admin/editUser", data)
        .then(response => {
          this.notifySuccess(text);
        })
        .catch(e => {});
    },
    ResetPassword(user) {
      this.resetUserId = user.id;
      this.resetUserName = user.username;
      this.showResetPasswordModal = true;
    },
    closeResetPasswordModal(user) {
      this.resetUserId = null;
      this.resetUserName = null;
      this.showResetPasswordModal = false;
    },
    reset2FA(user) {
      const data = {
        id: user.id,
      };

      this.$q
        .dialog({
          title: `Reset 2FA for ${user.username}?`,
          cancel: true,
          ok: { label: "Reset", color: "positive" },
        })
        .onOk(() => {
          this.$store.dispatch("admin/resetUserTOTP", data).then(response => {
            this.notifySuccess(response.data, 4000);
          });
        });
    },
    rowSelectedClass(id, selected) {
      if (selected.length !== 0 && selected[0].id === id) return this.$q.dark.isActive ? "highlight-dark" : "highlight";
    },
  },
  computed: {
    ...mapState({
      users: state => state.admin.users,
      logged_in_user: state => state.username,
    }),
  },
  mounted() {
    this.refresh();
  },
};
</script>