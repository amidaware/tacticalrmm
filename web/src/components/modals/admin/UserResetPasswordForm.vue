<template>
  <q-card style="width: 60vw">
    <q-form ref="form" @submit="submit">
      <q-card-section class="row items-center">
        <div class="text-h6">User Password Reset</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>
      <q-card-section class="row">
        <div class="col-2">New Password:</div>
        <div class="col-10">
          <q-input outlined dense v-model="password" :rules="[ val => !!val || '*Required']" />
        </div>
      </q-card-section>
      <q-card-section class="row items-center">
        <q-btn label="Reset" color="primary" type="submit" />
      </q-card-section>
    </q-form>
  </q-card>
</template>

<script>
import mixins, { notifySuccessConfig, notifyErrorConfig } from "@/mixins/mixins";

export default {
  name: "UserResetForm",
  mixins: [mixins],
  props: { pk: Number },
  data() {
    return {
      password: ""
    };
  },
  methods: {
    submit() {
      this.$q.loading.show();

      let formData = {
        id: this.pk,
        password: this.password
      };

      this.$store
        .dispatch("admin/resetUserPassword", formData)
        .then(r => {
          this.$q.loading.hide();
          this.$emit("close");
          this.$q.notify(notifySuccessConfig("User Password Reset!"));
        })
        .catch(e => {
          this.$q.loading.hide();
          this.$q.notify(notifyErrorConfig(e.response.data));
        });
    }
  }
};
</script>