<template>
  <div class="q-pa-md">
    <div class="row">
      <div class="col"></div>
      <div class="col">
        <q-card>
          <q-card-section class="row items-center">
            <div class="text-h6">Initial Setup</div>
          </q-card-section>
          <q-form @submit.prevent="finish">
            <q-card-section>
              <div>Add Client:</div>
              <q-input
                dense
                outlined
                v-model="firstclient"
                :rules="[ val => !!val || '*Required' ]"
              >
                <template v-slot:prepend>
                  <q-icon name="fas fa-user" />
                </template>
              </q-input>
            </q-card-section>
            <q-card-section>
              <div>Add Site:</div>
              <q-input dense outlined v-model="firstsite" :rules="[ val => !!val || '*Required' ]">
                <template v-slot:prepend>
                  <q-icon name="fas fa-map-marker-alt" />
                </template>
              </q-input>
            </q-card-section>
            <q-card-section>
              <div>Default timezone for agents:</div>
              <q-select dense outlined v-model="timezone" :options="allTimezones" />
            </q-card-section>
            <q-card-section>
              <div>Upload MeshAgent:</div>
              <div class="row">
                <q-input dense @input="val => { meshagent = val[0] }" filled type="file" />
              </div>
            </q-card-section>
            <q-card-actions align="center">
              <q-btn label="Finish" color="primary" type="submit" />
            </q-card-actions>
          </q-form>
        </q-card>
      </div>
      <div class="col"></div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";

export default {
  name: "InitialSetup",
  mixins: [mixins],
  data() {
    return {
      step: 1,
      firstclient: null,
      firstsite: null,
      meshagent: null,
      allTimezones: [],
      timezone: null
    };
  },
  methods: {
    finish() {
      if (!this.firstclient || !this.firstsite || !this.meshagent) {
        this.notifyError("Please upload your meshagent.exe");
      } else {
        this.$q.loading.show();
        const data = { client: this.firstclient, site: this.firstsite, timezone: this.timezone };
        axios
          .post("/clients/initialsetup/", data)
          .then(r => {
            let formData = new FormData();
            formData.append("meshagent", this.meshagent);
            axios
              .put("/api/v1/uploadmeshagent/", formData)
              .then(r => {
                this.$q.loading.hide();
                this.$router.push({ name: "Dashboard" });
              })
              .catch(e => {
                this.notifyError("error uploading");
                this.$q.loading.hide();
              });
          })
          .catch(err => {
            this.notifyError(err.response.data.error);
            this.$q.loading.hide();
          });
      }
    },
    getSettings() {
      axios.get("/core/getcoresettings/").then(r => {
        this.allTimezones = Object.freeze(r.data.all_timezones);
        this.timezone = r.data.default_time_zone;
      });
    }
  },
  created() {
    this.getSettings();
  }
};
</script>