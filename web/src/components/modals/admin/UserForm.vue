<template>
  <q-card style="width: 60vw">
    <q-form ref="form" @submit="onSubmit">
      <q-card-section class="row items-center">
        <div class="text-h6">{{ title }}</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Username:</div>
        <div class="col-10">
          <q-input outlined dense v-model="username" :rules="[val => !!val || '*Required']" class="q-pa-none" />
        </div>
      </q-card-section>
      <q-card-section class="row" v-if="!this.pk">
        <div class="col-2">Password:</div>
        <div class="col-10">
          <q-input
            outlined
            dense
            v-model="password"
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
            v-model="email"
            :rules="[val => isValidEmail(val) || 'Invalid email']"
            class="q-pa-none"
          />
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">First Name:</div>
        <div class="col-10">
          <q-input outlined dense v-model="first_name" />
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Last Name:</div>
        <div class="col-10">
          <q-input outlined dense v-model="last_name" />
        </div>
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">Active:</div>
        <div class="col-10">
          <q-toggle v-model="is_active" color="green" :disable="username === logged_in_user" />
        </div>
      </q-card-section>
      <q-card-section class="row items-center">
        <q-btn :label="title" color="primary" type="submit" />
      </q-card-section>
    </q-form>
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
      username: "",
      password: "",
      email: "",
      first_name: "",
      last_name: "",
      is_active: true,
      isPwd: true,
    };
  },
  computed: {
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

        this.username = r.data.username;
        this.email = r.data.email;
        this.is_active = r.data.is_active;
        this.first_name = r.data.first_name;
        this.last_name = r.data.last_name;
      });
    },
    onSubmit() {
      this.$q.loading.show();
      let formData = {
        id: this.pk,
        username: this.username,
        email: this.email,
        is_active: this.is_active,
        first_name: this.first_name,
        last_name: this.last_name,
      };

      if (this.pk) {
        // dont allow updating is_active if username is same as logged in user
        if (formData.username === this.logged_in_user) {
          delete formData.is_active;
        }

        this.$store
          .dispatch("admin/editUser", formData)
          .then(r => {
            this.$q.loading.hide();
            this.$emit("close");
            this.notifySuccess("User edited!");
          })
          .catch(e => {
            this.$q.loading.hide();
          });
      } else {
        formData.password = this.password;

        this.$store
          .dispatch("admin/addUser", formData)
          .then(r => {
            this.$q.loading.hide();
            this.$emit("close");
            this.notifySuccess(`User ${r.data} was added!`);
          })
          .catch(e => {
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
  },
};
</script>