<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card style="width: 50vw; max-width: 50vw">
      <q-bar>
        {{ title }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-form ref="form" @submit.prevent="onSubmit">
        <q-scroll-area :thumb-style="thumbStyle" style="height: 60vh">
          <q-card-section class="row">
            <div class="col-2 q-mt-sm">Name</div>
            <div class="col-10">
              <q-input outlined dense v-model="template.name" :rules="[val => !!val || '*Required']" />
            </div>
            <div class="col-12">
              <q-toggle v-model="template.is_active" color="green" label="Enabled" left-label />
            </div>

            <div class="col-2 q-my-sm">
              <span style="text-decoration: underline; cursor: help"
                >Failure action
                <q-tooltip>
                  Optionally run a script on an agent when it triggers an alert. This will be run once per alert, and
                  may run on any online agent.</q-tooltip
                >
              </span>
            </div>
            <div class="col-10 q-mb-sm">
              <q-select
                dense
                options-dense
                outlined
                v-model="template.action"
                :options="scriptOptions"
                map-options
                emit-value
              />
            </div>

            <div class="col-2 q-my-sm">Failure action args</div>
            <div class="col-10 q-mb-sm">
              <q-select
                dense
                label="Failure action arguments (press Enter after typing each argument)"
                filled
                v-model="template.action_args"
                use-input
                use-chips
                multiple
                hide-dropdown-icon
                input-debounce="0"
                new-value-mode="add"
              />
            </div>

            <div class="col-2">Failure action timeout (s)</div>
            <div class="col-10">
              <q-input
                outlined
                type="number"
                v-model.number="template.action_timeout"
                dense
                :rules="[
                  val => !!val || 'Failure action timeout is required',
                  val => val > 0 || 'Timeout must be greater than 0',
                  val => val <= 60 || 'Timeout must be 60 or less',
                ]"
              />
            </div>

            <div class="col-2 q-my-sm">
              <span style="text-decoration: underline; cursor: help"
                >Resolved action
                <q-tooltip>
                  Optionally run a script on an agent when the alert is resolved. This will be run once per alert, and
                  may run on any online agent.</q-tooltip
                >
              </span>
            </div>
            <div class="col-10 q-mb-sm">
              <q-select
                dense
                options-dense
                outlined
                v-model="template.resolved_action"
                :options="scriptOptions"
                map-options
                emit-value
              />
            </div>

            <div class="col-2 q-my-sm">Resolved action args</div>
            <div class="col-10 q-mb-sm">
              <q-select
                dense
                label="Resolved action arguments (press Enter after typing each argument)"
                filled
                v-model="template.resolved_action_args"
                use-input
                use-chips
                multiple
                hide-dropdown-icon
                input-debounce="0"
                new-value-mode="add"
              />
            </div>

            <div class="col-2">Resolved action timeout (s)</div>
            <div class="col-10">
              <q-input
                outlined
                type="number"
                v-model.number="template.resolved_action_timeout"
                dense
                :rules="[
                  val => !!val || 'Resolved action timeout is required',
                  val => val > 0 || 'Timeout must be greater than 0',
                  val => val <= 60 || 'Timeout must be 60 or less',
                ]"
              />
            </div>
          </q-card-section>

          <div class="q-pl-md text-subtitle1">Email Settings (Overrides global email settings)</div>
          <q-separator class="q-mb-sm" />

          <q-card-section class="row">
            <div class="col-2 q-mb-sm">Email recipients</div>
            <div class="col-4 q-mb-sm">
              <q-list dense v-if="template.email_recipients.length !== 0">
                <q-item v-for="email in template.email_recipients" :key="email" dense>
                  <q-item-section>
                    <q-item-label>{{ email }}</q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-icon class="cursor-pointer" name="delete" color="red" @click="removeEmail(email)" />
                  </q-item-section>
                </q-item>
              </q-list>
              <q-list v-else>
                <q-item-section>
                  <q-item-label>No recipients</q-item-label>
                </q-item-section>
              </q-list>
            </div>
            <div class="col-3 q-mb-sm"></div>
            <div class="col-3 q-mb-sm">
              <q-btn size="sm" icon="fas fa-plus" color="secondary" label="Add email" @click="toggleAddEmail" />
            </div>

            <div class="col-2 q-mt-sm">Email From address</div>
            <div class="col-10">
              <q-input class="q-mb-sm" outlined dense v-model="template.email_from" />
            </div>
          </q-card-section>

          <div class="q-pl-md text-subtitle1">SMS Settings (Overrides global SMS settings)</div>
          <q-separator class="q-mb-sm" />

          <q-card-section class="row">
            <div class="col-2 q-mb-sm">SMS recipients</div>
            <div class="col-4 q-mb-md">
              <q-list dense v-if="template.text_recipients.length !== 0">
                <q-item v-for="num in template.text_recipients" :key="num" dense>
                  <q-item-section>
                    <q-item-label>{{ num }}</q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-icon class="cursor-pointer" name="delete" color="red" @click="removeSMSNumber(num)" />
                  </q-item-section>
                </q-item>
              </q-list>
              <q-list v-else>
                <q-item-section>
                  <q-item-label>No recipients</q-item-label>
                </q-item-section>
              </q-list>
            </div>
            <div class="col-3 q-mb-sm"></div>
            <div class="col-3 q-mb-sm">
              <q-btn
                class="cursor-pointer"
                size="sm"
                icon="fas fa-plus"
                color="secondary"
                label="Add sms number"
                @click="toggleAddSMSNumber"
              />
            </div>
          </q-card-section>

          <div class="q-pl-md text-subtitle1">Agent Alert Settings</div>
          <q-separator class="q-mb-sm" />

          <q-card-section class="row">
            <div class="col-4">
              <q-toggle v-model="template.agent_email_on_resolved" color="green" left-label>
                <span style="text-decoration: underline; cursor: help"
                  >Email on resolved<q-tooltip>Sends an email when agent is back online</q-tooltip></span
                >
              </q-toggle>
            </div>

            <div class="col-4">
              <q-toggle v-model="template.agent_text_on_resolved" color="green" left-label>
                <span style="text-decoration: underline; cursor: help"
                  >Text on resolved<q-tooltip>Sends an SMS message when agent is back online</q-tooltip></span
                >
              </q-toggle>
            </div>
            <div class="col-4"></div>

            <div class="col-4">
              <q-toggle v-model="template.agent_always_email" color="green" left-label>
                <span style="text-decoration: underline; cursor: help"
                  >Always email<q-tooltip>Overrides the email alert option on the agent</q-tooltip></span
                >
              </q-toggle>
            </div>

            <div class="col-4">
              <q-toggle v-model="template.agent_always_text" color="green" left-label>
                <span style="text-decoration: underline; cursor: help"
                  >Always sms<q-tooltip>Overrides the sms alert option on the agent</q-tooltip></span
                >
              </q-toggle>
            </div>

            <div class="col-4">
              <q-toggle v-model="template.agent_always_alert" color="green" left-label>
                <span style="text-decoration: underline; cursor: help"
                  >Always dashboard alert<q-tooltip>Overrides the dashboard alert option on the agents</q-tooltip></span
                >
              </q-toggle>
            </div>

            <div class="col-12">
              <q-toggle v-model="template.agent_include_desktops" color="green" left-label>
                <span style="text-decoration: underline; cursor: help"
                  >Include desktops<q-tooltip>Includes desktop agent's offline alerts</q-tooltip></span
                >
              </q-toggle>
            </div>

            <div class="col-3 q-mt-sm">Periodic notification (days)</div>
            <div class="col-2">
              <q-input
                outlined
                type="number"
                v-model.number="template.agent_periodic_alert_days"
                dense
                :rules="[val => val >= 0 || 'Periodic days must be 0 or greater']"
              />
            </div>
          </q-card-section>

          <div class="q-pl-md text-subtitle1">Check Alert Settings</div>
          <q-separator class="q-mb-sm" />

          <q-card-section class="row">
            <div class="col-2 q-my-sm">
              <span style="text-decoration: underline; cursor: help"
                >Email on severity<q-tooltip>Sends a email only on selected severities</q-tooltip></span
              >
            </div>
            <div class="col-10 q-mb-sm">
              <q-select
                v-model="template.check_email_alert_severity"
                outlined
                dense
                options-dense
                multiple
                use-chips
                emit-value
                map-options
                :options="severityOptions"
              />
            </div>

            <div class="col-2 q-mt-sm">
              <span style="text-decoration: underline; cursor: help"
                >SMS on severity <q-tooltip>Sends a SMS message only on selected severities</q-tooltip></span
              >
            </div>
            <div class="col-10">
              <q-select
                v-model="template.check_text_alert_severity"
                outlined
                dense
                options-dense
                multiple
                use-chips
                emit-value
                map-options
                :options="severityOptions"
              />
            </div>

            <div class="col-2 q-mt-sm">
              <span style="text-decoration: underline; cursor: help"
                >Dashboard alert on severity
                <q-tooltip>Adds an alert in the dashboard only on selected severities</q-tooltip></span
              >
            </div>
            <div class="col-10 q-mt-sm">
              <q-select
                v-model="template.check_dashboard_alert_severity"
                outlined
                dense
                options-dense
                multiple
                use-chips
                emit-value
                map-options
                :options="severityOptions"
              />
            </div>

            <div class="col-4">
              <q-toggle v-model="template.check_email_on_resolved" color="green" left-label>
                <span style="text-decoration: underline; cursor: help"
                  >Email on resolved <q-tooltip>Sends an email when check alert has resolved</q-tooltip></span
                >
              </q-toggle>
            </div>

            <div class="col-4">
              <q-toggle v-model="template.check_text_on_resolved" color="green" left-label>
                <span style="text-decoration: underline; cursor: help"
                  >Text on resolved <q-tooltip>Sends an SMS message when check alert has resolved</q-tooltip></span
                >
              </q-toggle>
            </div>
            <div class="col-4"></div>

            <div class="col-4">
              <q-toggle v-model="template.check_always_email" color="green" left-label>
                <span style="text-decoration: underline; cursor: help"
                  >Always email <q-tooltip>Overrides the email alert setting on checks</q-tooltip></span
                >
              </q-toggle>
            </div>

            <div class="col-4">
              <q-toggle v-model="template.check_always_text" color="green" left-label>
                <span style="text-decoration: underline; cursor: help"
                  >Always sms <q-tooltip>Overrides the SMS alert setting on checks</q-tooltip></span
                >
              </q-toggle>
            </div>

            <div class="col-4">
              <q-toggle v-model="template.check_always_alert" color="green" left-label>
                <span style="text-decoration: underline; cursor: help"
                  >Always dashboard alert
                  <q-tooltip>Overrides the dashboard alert option on the agents</q-tooltip></span
                >
              </q-toggle>
            </div>

            <div class="col-3 q-mt-sm">Periodic notification (days)</div>
            <div class="col-2">
              <q-input
                outlined
                type="number"
                v-model.number="template.check_periodic_alert_days"
                dense
                :rules="[val => val >= 0 || 'Periodic days must be 0 or greater']"
              />
            </div>
          </q-card-section>

          <div class="q-pl-md text-subtitle1">Automated Task Alert Settings</div>
          <q-separator class="q-my-sm" />

          <q-card-section class="row">
            <div class="col-2 q-mb-sm">
              <span style="text-decoration: underline; cursor: help"
                >Email on severity
                <q-tooltip>Sends a email only on selected severities</q-tooltip>
              </span>
            </div>
            <div class="col-10 q-mb-sm">
              <q-select
                v-model="template.task_email_alert_severity"
                outlined
                dense
                options-dense
                multiple
                use-chips
                emit-value
                map-options
                :options="severityOptions"
              />
            </div>
            <div class="col-2 q-mt-sm">
              <span style="text-decoration: underline; cursor: help"
                >SMS on severity <q-tooltip>Sends an SMS message only on selected severities</q-tooltip></span
              >:
            </div>
            <div class="col-10">
              <q-select
                v-model="template.task_text_alert_severity"
                outlined
                dense
                options-dense
                multiple
                use-chips
                emit-value
                map-options
                :options="severityOptions"
              />
            </div>

            <div class="col-2 q-mt-sm">
              <span style="text-decoration: underline; cursor: help"
                >Dashboard alert on severity
                <q-tooltip>Adds an alert in the dashboard only on selected severities</q-tooltip></span
              >:
            </div>
            <div class="col-10 q-mt-sm">
              <q-select
                v-model="template.task_dashboard_alert_severity"
                outlined
                dense
                options-dense
                multiple
                use-chips
                emit-value
                map-options
                :options="severityOptions"
              />
            </div>

            <div class="col-4">
              <q-toggle v-model="template.task_email_on_resolved" color="green" left-label>
                <span style="text-decoration: underline; cursor: help"
                  >Email on resolved <q-tooltip>Sends an email when task alert has resolved</q-tooltip></span
                >
              </q-toggle>
            </div>

            <div class="col-4">
              <q-toggle v-model="template.task_text_on_resolved" color="green" left-label>
                <span style="text-decoration: underline; cursor: help"
                  >Text on resolved <q-tooltip>Sends an SMS message when task alert has resolved</q-tooltip></span
                >
              </q-toggle>
            </div>
            <div class="col-4"></div>

            <div class="col-4">
              <q-toggle v-model="template.task_always_email" color="green" left-label>
                <span style="text-decoration: underline; cursor: help"
                  >Always email <q-tooltip>Overrides the email alert option on the task</q-tooltip></span
                >
              </q-toggle>
            </div>

            <div class="col-4">
              <q-toggle v-model="template.task_always_text" color="green" left-label>
                <span style="text-decoration: underline; cursor: help"
                  >Always sms <q-tooltip>Overrides the SMS alert option on the task</q-tooltip></span
                >
              </q-toggle>
            </div>

            <div class="col-4">
              <q-toggle v-model="template.task_always_alert" color="green" left-label>
                <span style="text-decoration: underline; cursor: help"
                  >Always dashboard alert <q-tooltip>Overrides the dashboard alert option on the task</q-tooltip></span
                >
              </q-toggle>
            </div>

            <div class="col-3 q-mt-sm">Periodic notification (days)</div>
            <div class="col-2">
              <q-input
                outlined
                type="number"
                v-model.number="template.task_periodic_alert_days"
                dense
                :rules="[val => val >= 0]"
              />
            </div>
          </q-card-section>
        </q-scroll-area>

        <q-card-actions align="right">
          <q-btn dense flat label="Cancel" v-close-popup />
          <q-btn dense flat label="Save" color="primary" type="submit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "AlertTemplateForm",
  mixins: [mixins],
  props: { alertTemplate: Object },
  data() {
    return {
      template: {
        name: "",
        is_active: true,
        action: null,
        action_args: [],
        action_timeout: 15,
        resolved_action: null,
        resolved_action_args: [],
        resolved_action_timeout: 15,
        email_recipients: [],
        email_from: "",
        text_recipients: [],
        agent_include_desktops: false,
        agent_email_on_resolved: false,
        agent_text_on_resolved: false,
        agent_always_email: false,
        agent_always_text: false,
        agent_always_alert: false,
        agent_periodic_alert_days: 0,
        check_email_alert_severity: [],
        check_text_alert_severity: [],
        check_dashboard_alert_severity: [],
        check_email_on_resolved: false,
        check_text_on_resolved: false,
        check_always_email: false,
        check_always_text: false,
        check_always_alert: false,
        check_periodic_alert_days: 0,
        task_email_alert_severity: [],
        task_text_alert_severity: [],
        task_dashboard_alert_severity: [],
        task_email_on_resolved: false,
        task_text_on_resolved: false,
        task_always_email: false,
        task_always_text: false,
        task_always_alert: false,
        task_periodic_alert_days: 0,
      },
      scriptOptions: [],
      severityOptions: [
        { label: "Error", value: "error" },
        { label: "Warning", value: "warning" },
        { label: "Informational", value: "info" },
      ],
      thumbStyle: {
        right: "2px",
        borderRadius: "5px",
        backgroundColor: "#027be3",
        width: "5px",
        opacity: 0.75,
      },
    };
  },
  computed: {
    title() {
      return this.editing ? "Edit Alert Template" : "Add Alert Template";
    },
    editing() {
      return !!this.alertTemplate;
    },
  },
  methods: {
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
          this.template.email_recipients.push(data);
        });
    },
    toggleAddSMSNumber() {
      this.$q
        .dialog({
          title: "Add number",
          message:
            "Use E.164 format: must have the <b>+</b> symbol and <span class='text-red'>country code</span>, followed by the <span class='text-green'>phone number</span> e.g. <b>+<span class='text-red'>1</span><span class='text-green'>2131231234</span></b>",
          prompt: {
            model: "",
          },
          html: true,
          cancel: true,
          ok: { label: "Add", color: "primary" },
          persistent: false,
        })
        .onOk(data => {
          this.template.text_recipients.push(data);
        });
    },
    removeEmail(email) {
      const removed = this.template.email_recipients.filter(k => k !== email);
      this.template.email_recipients = removed;
    },
    removeSMSNumber(num) {
      const removed = this.template.text_recipients.filter(k => k !== num);
      this.template.text_recipients = removed;
    },
    onSubmit() {
      this.$q.loading.show();

      if (this.editing) {
        this.$axios
          .put(`alerts/alerttemplates/${this.template.id}/`, this.template)
          .then(r => {
            this.$q.loading.hide();
            this.onOk();
            this.notifySuccess("Alert Template edited!");
          })
          .catch(e => {
            this.$q.loading.hide();
            this.notifyError(e.response.data);
          });
      } else {
        this.$axios
          .post("alerts/alerttemplates/", this.template)
          .then(r => {
            this.$q.loading.hide();
            this.onOk();
            this.notifySuccess(`Alert Template was added!`);
          })
          .catch(e => {
            this.$q.loading.hide();
            this.notifyError(e);
          });
      }
    },
    getScripts() {
      this.$axios.get("/scripts/scripts/").then(r => {
        this.scriptOptions = r.data
          .map(script => ({ label: script.name, value: script.id }))
          .sort((a, b) => a.label.localeCompare(b.label));
      });
    },
    show() {
      this.$refs.dialog.show();
    },
    hide() {
      this.$refs.dialog.hide();
    },
    onHide() {
      this.$emit("hide");
    },
    onOk() {
      this.$emit("ok");
      this.hide();
    },
  },
  mounted() {
    this.getScripts();
    // Copy alertTemplate prop locally
    if (this.editing) Object.assign(this.template, this.alertTemplate);
  },
};
</script>