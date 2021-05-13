<template>
  <q-card style="min-width: 85vh">
    <q-form ref="form" @submit="onSubmit">
      <q-card-section class="row items-center">
        <div class="text-h6">{{ title }}</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

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
              <q-icon :name="isPwd ? 'visibility_off' : 'visibility'" class="cursor-pointer" @click="isPwd = !isPwd" />
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
          <q-toggle v-model="settings.is_active" color="green" :disable="settings.username === logged_in_user" />
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Role:</div>
        <template v-if="roles.length === 0"
          ><span>No roles have been created. Create some from Settings > Permissions Manager</span></template
        >
        <template v-else
          ><q-select
            map-options
            emit-value
            outlined
            dense
            options-dense
            v-model="settings.role"
            :options="roles"
            class="col-10"
        /></template>
      </q-card-section>
      <q-card-section class="row items-center">
        <q-btn :disable="!disableSave" label="Save" color="primary" type="submit" />
      </q-card-section>
    </q-form>
  </q-card>
</template>

<script>
import { mapState } from "vuex";
import mixins from "@/mixins/mixins";

export default {
  name: "UserForm",
  emits: ["close"],
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
        is_active: true,
        role: null,
      },
      roles: [],
      isPwd: true,
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
    getRoles() {
      this.$axios
        .get("/accounts/roles/")
        .then(r => {
          this.roles = r.data.map(role => ({ label: role.name, value: role.id }));
        })
        .catch(() => {});
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
    }
    this.getRoles();
  },
};
</script>