<template>
  <q-layout>
    <q-page-container>
      <q-page class="flex bg-image flex-center">
        <q-card v-bind:style="$q.screen.lt.sm?{'width': '80%'}:{'width':'30%'}">
          <q-card-section>
            <div class="text-center q-pt-lg">
              <div class="col text-h4 ellipsis">Tactical RMM</div>
            </div>
          </q-card-section>
          <q-card-section>
            <q-form @submit.prevent="checkCreds" class="q-gutter-md">
              <q-input
                filled
                v-model="credentials.username"
                label="Username"
                lazy-rules
                :rules="[ val => val && val.length > 0 || 'This field is required']"
              />

              <q-input
                type="password"
                filled
                v-model="credentials.password"
                label="Password"
                lazy-rules
                :rules="[ val => val && val.length > 0 || 'This field is required']"
              />

              <div>
                <q-btn label="Login" type="submit" color="primary" />
              </div>
            </q-form>
          </q-card-section>
        </q-card>
        <!-- 2 factor modal -->
        <q-dialog v-model="prompt">
          <q-card style="min-width: 400px">
            <q-form @submit.prevent="onSubmit">
              <q-card-section class="text-center text-h6">Two-Factor Token</q-card-section>

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
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";

export default {
  name: "Login",
  mixins: [mixins],
  data() {
    return {
      credentials: {},
      prompt: false
    };
  },

  methods: {
    checkCreds() {
      axios
        .post("/checkcreds/", this.credentials)
        .then(r => {
          this.prompt = true;
        })
        .catch(() => {
          this.notifyError("Bad credentials");
        });
    },
    onSubmit() {
      this.$store
        .dispatch("retrieveToken", this.credentials)
        .then(response => {
          this.credentials = {};
          this.$q.dark.set(false);
          this.$router.push({ name: "Dashboard" });
        })
        .catch(() => {
          this.credentials = {};
          this.prompt = false;
        });
    }
  },
  created() {
    this.$q.dark.set(true);
  }
};
</script>

<style>
.bg-image {
  background-image: linear-gradient(90deg, rgba(20, 20, 29, 1) 0%, rgba(38, 42, 56, 1) 49%, rgba(15, 18, 20, 1) 100%);
}
</style>
