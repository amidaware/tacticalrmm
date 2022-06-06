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
                v-model="client.name"
                :rules="[(val) => !!val || '*Required']"
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
                v-model="site.name"
                :rules="[(val) => !!val || '*Required']"
              >
                <template v-slot:prepend>
                  <q-icon name="apartment" />
                </template>
              </q-input>
            </q-card-section>
            <q-card-section>
              <div>Default timezone for agents:</div>
              <q-select
                dense
                options-dense
                outlined
                v-model="timezone"
                :options="allTimezones"
              />
            </q-card-section>
            <q-card-actions align="center">
              <q-btn
                label="Finish"
                color="primary"
                class="full-width"
                type="submit"
              />
            </q-card-actions>
          </q-form>
        </q-card>
      </div>
      <div class="col"></div>
    </div>
  </div>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "InitialSetup",
  mixins: [mixins],
  data() {
    return {
      client: {
        name: "",
      },
      site: {
        name: "",
      },
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
        site: this.site,
        timezone: this.timezone,
        initialsetup: true,
      };
      this.$axios
        .post("/clients/", data)
        .then(() => {
          this.$q.loading.hide();
          this.$router.push({ name: "Dashboard" });
        })
        .catch(() => this.$q.loading.hide());
    },
    getSettings() {
      this.$axios.get("/core/settings/").then((r) => {
        this.allTimezones = Object.freeze(r.data.all_timezones);
        this.timezone = r.data.default_time_zone;
      });
    },
  },
  mounted() {
    this.getSettings();
  },
};
</script>
