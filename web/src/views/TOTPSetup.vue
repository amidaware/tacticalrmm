<template>
  <div class="q-pa-md">
    <div class="row">
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
  </div>
</template>

<script>
import QrcodeVue from "qrcode.vue";

export default {
  name: "TOTPSetup",
  components: { QrcodeVue },
  data() {
    return {
      totp_key: "",
      qr_url: "",
    };
  },
  methods: {
    getQRCodeData() {
      this.$q.loading = true;

      const data = {
        username: this.$route.params.username,
      };

      this.$store
        .dispatch("admin/setupTOTP", data)
        .then(r => {
          this.$q.loading = false;

          if (r.data === "TOTP token already set") {
            this.$router.push({ name: "Login" });
          } else {
            this.totp_key = r.data.totp_key;
            this.qr_url = r.data.qr_url;
          }
        })
        .catch(e => {
          this.$q.loading = false;
          console.log(e.response);
        });
    },
    finish() {
      this.$router.push({ name: "Login" });
    },
  },
  created() {
    this.$q.dark.set(false);
    this.getQRCodeData();
  },
};
</script>
