<template>
  <div class="q-pa-md">
    <div class="row" v-if="valid">
      <div class="col"></div>
      <div class="col">
        <q-card>
          <q-card-section class="row items-center">
            <div class="text-h6">Setup 2-Factor</div>
          </q-card-section>
          <q-card-section>
            <p>
              Scan the QR Code with your authenticator app and then click
              Finish to be redirected back to the signin page.
            </p>
            <qrcode-vue :value="qr_url" size="200" level="H" />
          </q-card-section>
          <q-card-section>
            <p>You can also use the below code to configure the authenticator manually.</p>
            <p>{{ totp_key }}</p>
          </q-card-section>
          <q-card-actions align="center">
            <q-btn label="Finish" color="primary" class="full-width" @click="finish" />
          </q-card-actions>
        </q-card>
      </div>
      <div class="col"></div>
    </div>
    <div v-else>
      <q-dialog v-model="prompt" persistent>
        <q-card style="min-width: 400px">
          <q-form @submit.prevent="checkPass">
            <q-card-section class="text-center text-h6">Enter your password</q-card-section>

            <q-card-section>
              <q-input
                type="password"
                autofocus
                outlined
                v-model="password"
                :rules="[ val => val && val.length > 0 || 'This field is required']"
              />
            </q-card-section>

            <q-card-actions align="right" class="text-primary">
              <q-btn flat label="Submit" type="submit" />
            </q-card-actions>
          </q-form>
        </q-card>
      </q-dialog>
    </div>
  </div>
</template>

<script>
import QrcodeVue from "qrcode.vue";
import mixins from "@/mixins/mixins";

export default {
  name: "TOTPSetup",
  mixins: [mixins],
  components: { QrcodeVue },
  data() {
    return {
      totp_key: "",
      qr_url: "",
      password: null,
      valid: false,
      prompt: true,
    };
  },
  methods: {
    checkPass() {
      const data = {
        username: this.$route.params.username,
        password: this.password,
      };
      this.$axios
        .post("/checkcreds/", data)
        .then(r => {
          this.getQRCodeData();
        })
        .catch(() => {
          this.notifyError("Bad credentials");
        });
    },
    getQRCodeData() {
      this.$q.loading.show();
      const data = {
        username: this.$route.params.username,
      };

      this.$store
        .dispatch("admin/setupTOTP", data)
        .then(r => {
          this.$q.loading.hide();

          if (r.data === "TOTP token already set") {
            this.$router.push({ name: "Login" });
          } else {
            this.valid = true;
            this.prompt = false;
            this.totp_key = r.data.totp_key;
            this.qr_url = r.data.qr_url;
          }
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError(e.response.data);
        });
    },
    finish() {
      this.$router.push({ name: "Login" });
    },
  },
  created() {
    this.$q.dark.set(false);
  },
};
</script>
