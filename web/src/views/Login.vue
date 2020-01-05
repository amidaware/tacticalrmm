<template>
  <div class="q-pa-md">
    <div class="row text-center">
      <div class="col"></div>
      <div class="col">
        <h5>Tactical Techs RMM</h5>
        <q-form @submit.prevent="prompt = true" class="q-gutter-md">
          <q-input
            outlined
            v-model="credentials.username"
            label="Username"
            lazy-rules
            :rules="[ val => val && val.length > 0 || 'This field is required']"
          />

          <q-input
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
      </div>
      <div class="col"></div>
    </div>
    <!-- 2 factor modal -->
    <q-dialog v-model="prompt">
      <q-card style="min-width: 400px">
        <q-form @submit.prevent="onSubmit">
          <q-card-section class="text-center text-h5">Google Authenticator code</q-card-section>

          <q-card-section>
            <q-input
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