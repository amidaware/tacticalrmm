<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card style="width: 70vw; max-width: 70vw">
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
            <div class="col-2">Name:</div>
            <div class="col-10">
              <q-input outlined dense v-model="template.name" :rules="[val => !!val || '*Required']" />
            </div>
            <div class="col-2">Active:</div>
            <div class="col-10">
              <q-toggle v-model="template.is_active" color="green" />
            </div>
            <div class="col-2">Action:</div>
            <div class="col-10">
              <q-select
                hint="optionally run a set of scripts which an alert is triggered"
                dense
                options-dense
                outlined
                multiple
                v-model="template.actions"
                :options="scriptOptions"
                use-chips
                map-options
                emit-value
              />
            </div>
          </q-card-section>

          <div class="q-pl-md text-subtitle1">Email Settings</div>
          <q-separator class="q-mb-sm" />

          <q-card-section class="row">
            <div class="col-2 q-mb-sm">Email recipients:</div>
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

            <div class="col-2">Email From address:</div>
            <div class="col-10">
              <q-input
                hint="Will override the global settings From: address"
                class="q-mb-sm"
                outlined
                dense
                v-model="template.email_from"
              />
            </div>

            <div class="col-2">Email on severity:</div>
            <div class="col-10">
              <q-select
                v-model="template.email_alert_severity"
                outlined
                dense
                multiple
                use-chips
                emit-value
                map-options
                :options="severityOptions"
              />
            </div>

            <div class="col-2">Email on resolved:</div>
            <div class="col-4">
              <q-toggle v-model="template.email_on_resolved" color="green" />
            </div>
          </q-card-section>

          <div class="q-pl-md text-subtitle1">SMS Settings</div>
          <q-separator class="q-mb-sm" />

          <q-card-section class="row">
            <div class="col-2 q-mb-sm">SMS recipients:</div>
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

            <div class="col-2">SMS on severity:</div>
            <div class="col-10">
              <q-select
                v-model="template.text_alert_severity"
                outlined
                dense
                multiple
                use-chips
                emit-value
                map-options
                :options="severityOptions"
              />
            </div>

            <div class="col-2">SMS on resolved:</div>
            <div class="col-4">
              <q-toggle v-model="template.text_on_resolved" color="green" />
            </div>
          </q-card-section>

          <div class="q-pl-md text-subtitle1">Override agent alert settings</div>
          <q-separator class="q-mb-sm" />

          <q-card-section class="row">
            <div class="col-2">Always email:</div>
            <div class="col-4">
              <q-toggle v-model="template.always_email" color="green" />
            </div>
            <div class="col-2">Always sms:</div>
            <div class="col-4">
              <q-toggle v-model="template.always_text" color="green" />
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
        actions: [],
        name: "",
        is_active: true,
        always_email: false,
        always_text: false,
        email_recipients: [],
        email_from: "",
        email_alert_severity: [],
        text_alert_severity: [],
        text_recipients: [],
        email_on_resolved: false,
        text_on_resolved: false,
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
            this.onOK();
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
            this.onOK();
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
    onOK() {
      this.$emit("ok");
      this.hide();
    },
  },
  mounted() {
    // Copy alertTemplate prop locally
    if (this.editing) Object.assign(this.template, this.alertTemplate);

    this.getScripts();
  },
};
</script>