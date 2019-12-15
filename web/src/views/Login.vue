<template>
  <q-layout view="lHh Lpr lFf" class="bg-grey-9 text-white">
    <div class="window-height window-width row justify-center items-center">
      <div class="col"></div>
      <div class="col-3">
        <q-card dark class="bg-grey-9 shadow-10">
          <q-card-section class="text-center text-h5">Tactical Techs RMM</q-card-section>
          <q-card-section>
            <q-form @submit.prevent="prompt = true" class="q-gutter-md">
              <q-input
                dark
                outlined
                v-model="credentials.username"
                label="Username"
                lazy-rules
                :rules="[ val => val && val.length > 0 || 'This field is required']"
              />

              <q-input
                dark
                outlined
                type="password"
                v-model="credentials.password"
                label="Password"
                lazy-rules
                :rules="[ val => val && val.length > 0 || 'This field is required']"
              />
              <div>
                <q-btn label="Login" type="submit" color="primary" class="full-width q-mt-md" />
              </div>
            </q-form>
          </q-card-section>
        </q-card>
      </div>

      <div class="col"></div>
      <q-dialog v-model="prompt">
        <q-card dark class="bg-grey-9" style="min-width: 400px">
          <q-form @submit.prevent="onSubmit">
            <q-card-section class="text-center text-h5">
              Google Authenticator code
            </q-card-section>

            <q-card-section>
              <q-input
                dark
                autofocus
                outlined
                v-model="credentials.twofactor"
                :rules="[ val => val && val.length > 0 || 'This field is required']"
              />
            </q-card-section>

            <q-card-actions align="right" class="text-primary">
              <q-btn flat label="Cancel" v-close-popup />
              <q-btn flat label="Submit" type="submit" />
            </q-card-actions>
          </q-form>
        </q-card>
      </q-dialog>
    </div>
  </q-layout>
</template>

<script>
export default {
  name: "Login",
  data() {
    return {
      credentials: {},
      prompt: false
    };
  },

  methods: {
    onSubmit() {
      this.$store
        .dispatch("retrieveToken", this.credentials)
        .then(response => {
          this.credentials = {};
          this.$router.push({ name: "Dashboard" });
        })
        .catch(() => {
          this.credentials = {};
          this.prompt = false;
        });
    }
  }
};
</script>