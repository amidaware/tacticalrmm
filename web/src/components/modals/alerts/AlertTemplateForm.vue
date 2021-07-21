<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card style="width: 90vw; max-width: 90vw">
      <q-bar>
        {{ title }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-stepper v-model="step" ref="stepper" alternative-labels header-nav color="primary" animated>
        <q-step :name="1" :error="!template.name && step > 1" title="General Settings" icon="settings">
          <q-card flat>
            <q-card-section>
              <q-input
                label="Name"
                class="q-mb-none"
                outlined
                dense
                v-model="template.name"
                :rules="[val => !!val || '*Required']"
              />
            </q-card-section>

            <q-card-section>
              <q-toggle v-model="template.is_active" color="green" label="Enabled" left-label />
            </q-card-section>

            <div class="q-pl-md text-subtitle1">Email Settings (Overrides global email settings)</div>

            <q-card-section>
              <q-input label="Email From address" class="q-mb-sm" outlined dense v-model="template.email_from" />
            </q-card-section>

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
            </q-card-section>

            <div class="q-pl-md text-subtitle1">SMS Settings (Overrides global SMS settings)</div>

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
          </q-card>
        </q-step>

        <q-step :name="2" title="Alert Actions" icon="warning">
          <q-card flat>
            <div class="q-pl-md text-subtitle1">
              <span style="text-decoration: underline; cursor: help"
                >Alert Failure Settings
                <q-tooltip>
                  The selected script will run when an alert is triggered. This script will run on any online agent.
                </q-tooltip>
              </span>
            </div>

            <q-card-section>
              <q-select
                class="q-mb-sm"
                label="Failure action"
                dense
                options-dense
                outlined
                clearable
                v-model="template.action"
                :options="scriptOptions"
                map-options
                emit-value
                @update:model-value="setScriptDefaults('failure')"
              >
                <template v-slot:option="scope">
                  <q-item v-if="!scope.opt.category" v-bind="scope.itemProps" class="q-pl-lg">
                    <q-item-section>
                      <q-item-label v-html="scope.opt.label"></q-item-label>
                    </q-item-section>
                  </q-item>
                  <q-item-label v-if="scope.opt.category" v-bind="scope.itemProps" header class="q-pa-sm">{{
                    scope.opt.category
                  }}</q-item-label>
                </template>
              </q-select>

              <q-select
                class="q-mb-sm"
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

              <q-input
                class="q-mb-sm"
                label="Failure action timeout (seconds)"
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
            </q-card-section>

            <div class="q-pl-md text-subtitle1">
              <span style="text-decoration: underline; cursor: help"
                >Alert Resolved Settings
                <q-tooltip>
                  The selected script will run when an alert is resolved. This script will run on any online agent.
                </q-tooltip>
              </span>
            </div>

            <q-card-section>
              <q-select
                class="q-mb-sm"
                label="Resolved Action"
                dense
                options-dense
                outlined
                clearable
                v-model="template.resolved_action"
                :options="scriptOptions"
                map-options
                emit-value
                @update:model-value="setScriptDefaults('resolved')"
              >
                <template v-slot:option="scope">
                  <q-item v-if="!scope.opt.category" v-bind="scope.itemProps" class="q-pl-lg">
                    <q-item-section>
                      <q-item-label v-html="scope.opt.label"></q-item-label>
                    </q-item-section>
                  </q-item>
                  <q-item-label v-if="scope.opt.category" v-bind="scope.itemProps" header class="q-pa-sm">{{
                    scope.opt.category
                  }}</q-item-label>
                </template>
              </q-select>

              <q-select
                class="q-mb-sm"
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

              <q-input
                class="q-mb-sm"
                label="Resolved action timeout (seconds)"
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
            </q-card-section>

            <div class="q-pl-md text-subtitle1">
              <span style="text-decoration: underline; cursor: help"
                >Run actions only on
                <q-tooltip> The selected script will only run on the following types of alerts </q-tooltip>
              </span>
            </div>

            <q-card-section>
              <q-toggle v-model="template.agent_script_actions" label="Agents" color="green" left-label />

              <q-toggle v-model="template.check_script_actions" label="Checks" color="green" left-label />

              <q-toggle v-model="template.task_script_actions" label="Tasks" color="green" left-label />
            </q-card-section>
          </q-card>
        </q-step>

        <q-step :name="3" title="Agent Overdue Settings" icon="devices">
          <q-card flat>
            <div class="q-pl-md text-subtitle1">
              <span style="text-decoration: underline; cursor: help"
                >Alert Failure Settings
                <q-tooltip>
                  Select what notifications should be sent when an agent is overdue. Enabled will override the agent
                  notification setting sand always notify. Not configured will use what notification settings are
                  configured on the agent. Disabled will override the agent notification settings and never notify.
                </q-tooltip>
              </span>
            </div>
            <q-card-section>
              <q-toggle
                v-model="template.agent_always_email"
                label="Email"
                color="green"
                left-label
                toggle-indeterminate
              />
              <q-toggle
                v-model="template.agent_always_text"
                label="Text"
                color="green"
                left-label
                toggle-indeterminate
              />
              <q-toggle
                v-model="template.agent_always_alert"
                label="Dashboard"
                color="green"
                left-label
                toggle-indeterminate
              />
            </q-card-section>
            <q-card-section>
              <q-input
                label="Alert again if not resolved after (days)"
                outlined
                type="number"
                v-model.number="template.agent_periodic_alert_days"
                dense
                :rules="[val => val >= 0 || 'Periodic days must be 0 or greater']"
              />
            </q-card-section>

            <div class="q-pl-md text-subtitle1">
              <span style="text-decoration: underline; cursor: help"
                >Alert Resolved Settings
                <q-tooltip> Select what notifications should be sent when an overdue agent is back online. </q-tooltip>
              </span>
            </div>
            <q-card-section>
              <q-toggle v-model="template.agent_email_on_resolved" label="Email" color="green" left-label />
              <q-toggle v-model="template.agent_text_on_resolved" label="Text" color="green" left-label />
            </q-card-section>
          </q-card>
        </q-step>

        <q-step :name="4" title="Check Settings" icon="fas fa-check-double">
          <q-card flat>
            <div class="q-pl-md text-subtitle1">
              <span style="text-decoration: underline; cursor: help"
                >Alert Failure Settings
                <q-tooltip>
                  Select what notifications are sent when a check fails. Enabled will override the check notification
                  settings and always notify. Not configured will use the notification settings configured on the check.
                  Disabled will override the check notification settings and never notify.
                </q-tooltip>
              </span>
            </div>

            <q-card-section>
              <q-toggle
                v-model="template.check_always_email"
                label="Email"
                color="green"
                left-label
                toggle-indeterminate
              />
              <q-toggle
                v-model="template.check_always_text"
                label="Text"
                color="green"
                left-label
                toggle-indeterminate
              />
              <q-toggle
                v-model="template.check_always_alert"
                label="Dashboard"
                color="green"
                left-label
                toggle-indeterminate
              />
            </q-card-section>

            <q-card-section>
              <q-select
                label="Only email on alert severity"
                hint="This needs to be set in order to receive email notifications"
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
            </q-card-section>

            <q-card-section>
              <q-select
                label="Only text on alert severity"
                hint="This needs to be set in order to receive text notifications"
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
            </q-card-section>

            <q-card-section>
              <q-select
                label="Only show dashboard alert on severity"
                hint="This needs to be set in order to receive dashboard notifications"
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
            </q-card-section>

            <q-card-section>
              <q-input
                label="Alert again if not resolved after (days)"
                outlined
                type="number"
                v-model.number="template.check_periodic_alert_days"
                dense
                :rules="[val => val >= 0 || 'Periodic days must be 0 or greater']"
              />
            </q-card-section>

            <div class="q-pl-md text-subtitle1">
              <span style="text-decoration: underline; cursor: help"
                >Alert Resolved Settings
                <q-tooltip> Select what notifications are sent when a failed check is resolved. </q-tooltip>
              </span>
            </div>
            <q-card-section>
              <q-toggle v-model="template.check_email_on_resolved" label="Email" color="green" left-label />
              <q-toggle v-model="template.check_text_on_resolved" label="Text" color="green" left-label />
            </q-card-section>
          </q-card>
        </q-step>

        <q-step :name="5" title="Automated Task Settings" icon="fas fa-tasks">
          <q-card flat>
            <div class="q-pl-md text-subtitle1">
              <span style="text-decoration: underline; cursor: help"
                >Alert Failure Settings
                <q-tooltip>
                  Select what notifications are sent when an automated task fails. Enabled will override the task
                  notification settings and always notify. Not configured will use the notification settings configured
                  on the task. Disabled will override the task notification settings and never notify.
                </q-tooltip>
              </span>
            </div>

            <q-card-section>
              <q-toggle
                v-model="template.task_always_email"
                label="Email"
                color="green"
                left-label
                toggle-indeterminate
              />
              <q-toggle
                v-model="template.task_always_text"
                label="Text"
                color="green"
                left-label
                toggle-indeterminate
              />
              <q-toggle
                v-model="template.task_always_alert"
                label="Dashboard"
                color="green"
                left-label
                toggle-indeterminate
              />
            </q-card-section>

            <q-card-section>
              <q-select
                label="Only email on alert severity"
                hint="This needs to be set in order to receive email notifications"
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
            </q-card-section>

            <q-card-section>
              <q-select
                label="Only text on alert severity"
                hint="This needs to be set in order to receive text notifications"
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
            </q-card-section>

            <q-card-section>
              <q-select
                label="Only show dashboard alert on severity"
                hint="This needs to be set in order to receive dashboard notifications"
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
            </q-card-section>

            <q-card-section>
              <q-input
                label="Alert again if not resolved (days)"
                outlined
                type="number"
                v-model.number="template.task_periodic_alert_days"
                dense
                :rules="[val => val >= 0 || 'Periodic days must be 0 or greater']"
              />
            </q-card-section>

            <div class="q-pl-md text-subtitle1">
              <span style="text-decoration: underline; cursor: help"
                >Alert Resolved Settings
                <q-tooltip> Select what notifications are sent when a failed task is resolved. </q-tooltip>
              </span>
            </div>
            <q-card-section>
              <q-toggle v-model="template.task_email_on_resolved" label="Email" color="green" left-label />
              <q-toggle v-model="template.check_text_on_resolved" label="Text" color="green" left-label />
            </q-card-section>
          </q-card>
        </q-step>
        <template v-slot:navigation>
          <q-stepper-navigation class="row">
            <q-btn
              v-if="step > 1"
              flat
              color="primary"
              @click="$refs.stepper.previous()"
              label="Back"
              class="q-mr-xs"
            />
            <q-btn v-if="step < 5" @click="$refs.stepper.next()" color="primary" label="Next" />
            <q-space />
            <q-btn @click="onSubmit" color="primary" label="Submit" />
          </q-stepper-navigation>
        </template>
      </q-stepper>
    </q-card>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";
import { mapGetters } from "vuex";

export default {
  name: "AlertTemplateForm",
  emits: ["hide", "ok", "cancel"],
  mixins: [mixins],
  props: { alertTemplate: Object },
  data() {
    return {
      step: 1,
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
        agent_email_on_resolved: false,
        agent_text_on_resolved: false,
        agent_always_email: null,
        agent_always_text: null,
        agent_always_alert: null,
        agent_periodic_alert_days: 0,
        agent_script_actions: true,
        check_email_alert_severity: [],
        check_text_alert_severity: [],
        check_dashboard_alert_severity: [],
        check_email_on_resolved: false,
        check_text_on_resolved: false,
        check_always_email: null,
        check_always_text: null,
        check_always_alert: null,
        check_periodic_alert_days: 0,
        check_script_actions: true,
        task_email_alert_severity: [],
        task_text_alert_severity: [],
        task_dashboard_alert_severity: [],
        task_email_on_resolved: false,
        task_text_on_resolved: false,
        task_always_email: null,
        task_always_text: null,
        task_always_alert: null,
        task_periodic_alert_days: 0,
        task_script_actions: true,
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
    ...mapGetters(["showCommunityScripts"]),
    title() {
      return this.editing ? "Edit Alert Template" : "Add Alert Template";
    },
    editing() {
      return !!this.alertTemplate;
    },
  },
  methods: {
    setScriptDefaults(type) {
      if (type === "failure") {
        const script = this.scriptOptions.find(i => i.value === this.template.action);
        this.template.action_args = script.args;
      } else if (type === "resolved") {
        const script = this.scriptOptions.find(i => i.value === this.template.resolved_action);
        this.template.resolved_action_args = script.args;
      }
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
      if (!this.template.name) {
        this.notifyError("Name needs to be set");
        return;
      }

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
          });
      }
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
    this.getScriptOptions(this.showCommunityScripts).then(options => (this.scriptOptions = Object.freeze(options)));
    // Copy alertTemplate prop locally
    if (this.editing) Object.assign(this.template, this.alertTemplate);
  },
};
</script>
