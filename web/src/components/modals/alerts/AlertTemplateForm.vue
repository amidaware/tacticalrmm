<template>
  <q-card style="width: 70vw">
    <q-bar>
      {{ title }}
      <q-space />
      <q-btn dense flat icon="close" v-close-popup>
        <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
      </q-btn>
    </q-bar>
    <q-form ref="form" @submit="onSubmit">
      <q-card-section class="row">
        <div class="col-2">Name:</div>
        <div class="col-10">
          <q-input outlined dense v-model="name" :rules="[val => !!val || '*Required']" class="q-pa-none" />
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
  name: "AlertTemplateForm",
  mixins: [mixins],
  props: { alertTemplate: Object },
  data() {
    return {};
  },
  computed: {
    title() {
      return this.editing ? "Edit User" : "Add User";
    },
    editing() {
      return !!this.alertTemplate;
    },
  },
  methods: {
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

      if (this.editing) {
        // dont allow updating is_active if username is same as logged in user
        if (formData.username === this.logged_in_user) {
          delete formData.is_active;
        }

        this.$store
          .dispatch("admin/editUser", formData)
          .then(r => {
            this.$q.loading.hide();
            this.$emit("close");
            this.$q.notify(notifySuccessConfig("User edited!"));
          })
          .catch(e => {
            this.$q.loading.hide();
            this.$q.notify(notifyErrorConfig(e.response.data));
          });
      } else {
        formData.password = this.password;

        this.$store
          .dispatch("admin/addUser", formData)
          .then(r => {
            this.$q.loading.hide();
            this.$emit("close");
            this.$q.notify(notifySuccessConfig(`User ${r.data} was added!`));
          })
          .catch(e => {
            this.$q.loading.hide();
            this.$q.notify(notifyErrorConfig(e.response.data));
          });
      }
    },
  },
};
</script>