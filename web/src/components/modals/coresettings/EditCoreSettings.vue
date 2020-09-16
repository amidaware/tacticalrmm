<template>
  <q-card style="min-width: 85vh">
    <q-splitter v-model="splitterModel">
      <template v-slot:before>
        <q-tabs dense v-model="tab" vertical class="text-primary">
          <q-tab name="general" label="General" />
          <q-tab name="alerts" label="Alerts" />
          <q-tab name="meshcentral" label="MeshCentral" />
        </q-tabs>
      </template>
      <template v-slot:after>
        <q-form @submit.prevent="editSettings">
          <q-card-section class="row items-center">
            <div class="text-h6">Global Settings</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </q-card-section>
          <q-scroll-area :thumb-style="thumbStyle" style="height: 60vh;">
            <q-tab-panels
              v-model="tab"
              animated
              transition-prev="jump-up"
              transition-next="jump-up"
            >
              <!-- general -->
              <q-tab-panel name="general">
                <div class="text-subtitle2">General</div>
                <hr />
                <q-card-section class="row">
                  <q-checkbox
                    v-model="settings.agent_auto_update"
                    label="Enable agent automatic self update"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Default agent timezone:</div>
                  <div class="col-2"></div>
                  <q-select
                    outlined
                    dense
                    options-dense
                    v-model="settings.default_time_zone"
                    :options="allTimezones"
                    class="col-6"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Default server policy:</div>
                  <div class="col-2"></div>
                  <q-select
                    clearable
                    map-options
                    emit-value
                    outlined
                    dense
                    options-dense
                    v-model="settings.server_policy"
                    :options="policies"
                    class="col-6"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Default workstation policy:</div>
                  <div class="col-2"></div>
                  <q-select
                    clearable
                    map-options
                    emit-value
                    outlined
                    dense
                    options-dense
                    v-model="settings.workstation_policy"
                    :options="policies"
                    class="col-6"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Reset Patch Policy on Agents:</div>
                  <div class="col-2"></div>
                  <q-btn color="negative" label="Reset" @click="resetPatchPolicyModal" />
                </q-card-section>
              </q-tab-panel>
              <!-- alerts -->
              <q-tab-panel name="alerts">
                <div class="text-subtitle2 row">
                  <div>Email Alert Routing</div>
                  <q-space />
                  <div>
                    <q-btn
                      size="sm"
                      color="grey-5"
                      icon="fas fa-plus"
                      text-color="black"
                      label="Add emails"
                      @click="toggleAddEmail"
                    />
                  </div>
                </div>
                <hr />
                <q-card-section class="row">
                  <div class="col-3">Recipients</div>
                  <div class="col-4"></div>
                  <div class="col-5">
                    <q-list
                      bordered
                      dense
                      v-if="ready && settings.email_alert_recipients.length !== 0"
                    >
                      <q-item
                        v-for="email in settings.email_alert_recipients"
                        :key="email"
                        clickable
                        v-ripple
                        @click="removeEmail(email)"
                      >
                        <q-item-section>
                          <q-item-label>{{ email }}</q-item-label>
                        </q-item-section>
                        <q-item-section side>
                          <q-icon name="delete" color="red" />
                        </q-item-section>
                      </q-item>
                    </q-list>
                    <q-list v-else>
                      <q-item-section>
                        <q-item-label>No recipients</q-item-label>
                      </q-item-section>
                    </q-list>
                  </div>
                </q-card-section>
                <!-- smtp -->
                <div class="text-subtitle2">SMTP Settings</div>
                <hr />
                <q-card-section class="row">
                  <div class="col-2">From:</div>
                  <div class="col-4"></div>
                  <q-input
                    outlined
                    dense
                    v-model="settings.smtp_from_email"
                    class="col-6 q-pa-none"
                    :rules="[val => isValidEmail(val) || 'Invalid email']"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">Host:</div>
                  <div class="col-4"></div>
                  <q-input outlined dense v-model="settings.smtp_host" class="col-6 q-pa-none" />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">Port:</div>
                  <div class="col-4"></div>
                  <q-input
                    dense
                    v-model.number="settings.smtp_port"
                    type="number"
                    filled
                    class="q-pa-none"
                    :rules="[ val => val > 0 && val <= 65535 || 'Invalid Port']"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <q-checkbox
                    v-model="settings.smtp_requires_auth"
                    label="My Server Requires Authentication"
                    class="q-pa-none"
                  />
                </q-card-section>
                <q-card-section class="row" v-show="settings.smtp_requires_auth">
                  <div class="col-2">Username:</div>
                  <div class="col-4"></div>
                  <q-input
                    outlined
                    dense
                    v-model="settings.smtp_host_user"
                    class="col-6 q-pa-none"
                  />
                </q-card-section>
                <q-card-section class="row" v-show="settings.smtp_requires_auth">
                  <div class="col-2">Password:</div>
                  <div class="col-4"></div>
                  <q-input
                    outlined
                    dense
                    class="col-6 q-pa-none"
                    v-model="settings.smtp_host_password"
                    :type="isPwd ? 'password' : 'text'"
                  >
                    <template v-slot:append>
                      <q-icon
                        :name="isPwd ? 'visibility_off' : 'visibility'"
                        class="cursor-pointer"
                        @click="isPwd = !isPwd"
                      />
                    </template>
                  </q-input>
                </q-card-section>
              </q-tab-panel>
              <!-- meshcentral -->
              <q-tab-panel name="meshcentral">
                <div class="text-subtitle2">MeshCentral Settings</div>
                <hr />
                <q-card-section class="row">
                  <div class="col-4">Username:</div>
                  <div class="col-2"></div>
                  <q-input dense filled v-model="settings.mesh_username" class="col-6" />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Mesh Site:</div>
                  <div class="col-2"></div>
                  <q-input dense filled v-model="settings.mesh_site" class="col-6" />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Mesh Token:</div>
                  <div class="col-2"></div>
                  <q-input dense filled v-model="settings.mesh_token" class="col-6" />
                </q-card-section>
              </q-tab-panel>
            </q-tab-panels>
          </q-scroll-area>
          <q-card-section class="row items-center">
            <q-btn label="Save" color="primary" type="submit" />
            <q-btn
              v-show="tab === 'alerts'"
              label="Save and Test"
              color="primary"
              type="submit"
              class="q-ml-md"
              @click="emailTest = true"
            />
          </q-card-section>
        </q-form>
      </template>
    </q-splitter>

    <q-dialog v-model="showResetPatchPolicyModal">
      <ResetPatchPolicy @close="showResetPatchPolicyModal = false" />
    </q-dialog>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
import { mapState } from "vuex";
import ResetPatchPolicy from "@/components/modals/coresettings/ResetPatchPolicy";

export default {
  name: "EditCoreSettings",
  components: { ResetPatchPolicy },
  mixins: [mixins],
  data() {
    return {
      showResetPatchPolicyModal: false,
      ready: false,
      settings: {},
      email: null,
      AddEmailModal: false,
      tab: "general",
      splitterModel: 15,
      isPwd: true,
      allTimezones: [],
      emailTest: false,
      thumbStyle: {
        right: "2px",
        borderRadius: "5px",
        backgroundColor: "#027be3",
        width: "5px",
        opacity: 0.75,
      },
    };
  },
  methods: {
    getCoreSettings() {
      axios.get("/core/getcoresettings/").then(r => {
        this.settings = r.data;
        this.allTimezones = Object.freeze(r.data.all_timezones);
        this.ready = true;
      });
    },
    getPolicies() {
      this.$store.dispatch("automation/loadPolicies").catch(e => {
        this.notifyError(e.response.data);
      });
    },
    toggleAddEmail() {
      this.$q
        .dialog({
          title: "Add email",
          prompt: {
            model: "",
            isValid: val => this.isValidEmail(val),
            type: "email",
          },
          cancel: true,
          ok: { label: "Add", color: "primary" },
          persistent: false,
        })
        .onOk(data => {
          this.settings.email_alert_recipients.push(data);
        });
    },
    removeEmail(email) {
      const removed = this.settings.email_alert_recipients.filter(k => k !== email);
      this.settings.email_alert_recipients = removed;
    },
    resetPatchPolicyModal() {
      this.showResetPatchPolicyModal = true;
    },
    editSettings() {
      this.$q.loading.show();
      axios
        .patch("/core/editsettings/", this.settings)
        .then(r => {
          this.$q.loading.hide();
          if (this.emailTest) {
            this.$q.loading.show({ message: "Sending test email..." });
            this.$axios
              .get("/core/emailtest/")
              .then(r => {
                this.$q.loading.hide();
                this.getCoreSettings();
                this.notifySuccess(r.data, 3000);
              })
              .catch(e => {
                this.$q.loading.hide();
                this.notifyError(e.response.data, 7000);
              });
          } else {
            this.$emit("close");
            this.notifySuccess("Settings were edited!");
          }
        })
        .catch(() => {
          this.$q.loading.hide();
          this.notifyError("You have some invalid input. Please check all fields");
        });
    },
  },
  computed: {
    ...mapState({
      policies: state => state.automation.policies.map(policy => ({ label: policy.name, value: policy.id })),
    }),
  },
  created() {
    this.getCoreSettings();
    this.getPolicies();
  },
};
</script>