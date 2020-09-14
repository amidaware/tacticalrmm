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
                v-model="client.client"
                :rules="[ val => !!val || '*Required' ]"
              >
                <template v-slot:prepend>
                  <q-icon name="business" />
                </template>
              </q-input>
            </q-card-section>
            <q-card-section>
              <div>Add Site:</div>
              <q-input
                dense
                outlined
                v-model="client.site"
                :rules="[ val => !!val || '*Required' ]"
              >
                <template v-slot:prepend>
                  <q-icon name="apartment" />
                </template>
              </q-input>
            </q-card-section>
            <q-card-section>
              <div>Default timezone for agents:</div>
              <q-select dense options-dense outlined v-model="timezone" :options="allTimezones" />
            </q-card-section>
            <q-card-section>
              <div class="row">
                <q-file
                  v-model="meshagent"
                  :rules="[ val => !!val || '*Required' ]"
                  label="Upload MeshAgent"
                  stack-label
                  filled
                  counter
                  accept=".exe"
                >
                  <template v-slot:prepend>
                    <q-icon name="attach_file" />
                  </template>
                </q-file>
              </div>
            </q-card-section>
            <q-card-actions align="center">
              <q-btn label="Finish" color="primary" class="full-width" type="submit" />
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
      client: {
        client: null,
        site: null,
      },
      meshagent: null,
      allTimezones: [],
      timezone: null,
      arch: "64",
    };
  },
  methods: {
    finish() {
      this.$q.loading.show();
      const data = {
        client: this.client,
        timezone: this.timezone,
        initialsetup: true,
      };
      axios
        .post("/clients/clients/", data)
        .then(r => {
          let formData = new FormData();
          formData.append("arch", this.arch);
          formData.append("meshagent", this.meshagent);
          axios
            .put("/core/uploadmesh/", formData)
            .then(() => {
              this.$q.loading.hide();
              this.$router.push({ name: "Dashboard" });
            })
            .catch(e => {
              this.$q.loading.hide();
              this.notifyError("error uploading");
            });
        })
        .catch(e => {
          this.$q.loading.hide();
          if (e.response.data.client) {
            this.notifyError(e.response.data.client);
          } else {
            this.notifyError(e.response.data.non_field_errors);
          }
        });
    },
    getSettings() {
      axios.get("/core/getcoresettings/").then(r => {
        this.allTimezones = Object.freeze(r.data.all_timezones);
        this.timezone = r.data.default_time_zone;
      });
    },
  },
  created() {
    this.getSettings();
  },
};
</script>