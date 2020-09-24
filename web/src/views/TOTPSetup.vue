<template>
  <div class="q-pa-md">
    <div class="row">
      <div class="col"></div>
      <div class="col">
        <q-card>
          <q-card-section class="row items-center">
            <div class="text-h6">Setup 2-Factor</div>
          </q-card-section>
          <q-card-section v-if="qr_url">
            <p>
              Scan the QR Code with your authenticator app and then click Finish to be redirected back to the signin
              page. If you navigate away from this page you 2FA signin will need to be reset!
            </p>
            <qrcode-vue :value="qr_url" size="200" level="H" />
          </q-card-section>
          <q-card-section v-if="totp_key">
            <p>You can also use the below code to configure the authenticator manually.</p>
            <p>{{ totp_key }}</p>
          </q-card-section>
          <q-card-actions align="center">
            <q-btn label="Finish" color="primary" class="full-width" @click="logout" />
          </q-card-actions>
        </q-card>
      </div>
      <div class="col"></div>
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
      totp_key: null,
      qr_url: null,
      cleared_token: false,
    };
  },
  methods: {
    getQRCodeData() {
      this.$q.loading.show();

      this.$store
        .dispatch("admin/setupTOTP")
        .then(r => {
          this.$q.loading.hide();

          if (r.data === "TOTP token already set") {
            //don't logout user if totp is already set
            this.cleared_token = true;
            this.$router.push({ name: "Login" });
          } else {
            this.totp_key = r.data.totp_key;
            this.qr_url = r.data.qr_url;
          }
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    logout() {
      this.$q.loading.show();
      this.$store
        .dispatch("destroyToken")
        .then(r => {
          this.cleared_token = true;
          this.$q.loading.hide();
          this.$router.push({ name: "Login" });
        })
        .catch(() => {
          this.cleared_token = true;
          this.$q.loading.hide();
          this.$router.push({ name: "Login" });
        });
    },
  },
  created() {
    this.getQRCodeData();
    this.$q.dark.set(false);
  },
  beforeDestroy() {
    if (!this.cleared_token) {
      this.logout();
    }
  },
};
</script>
