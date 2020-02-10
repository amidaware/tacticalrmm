<template>
  <q-card style="min-width: 700px">
    <q-splitter v-model="splitterModel" style="height: 700px">
      <template v-slot:before>
        <q-tabs dense v-model="tab" vertical class="text-primary">
          <q-tab name="general" label="General" />
          <q-tab name="patch" label="Patches" />
        </q-tabs>
      </template>
      <template v-slot:after>
        <q-form @submit.prevent="editAgent">
          <q-card-section class="row items-center">
            <div class="text-h6">Edit {{ hostname }}</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </q-card-section>
          <q-tab-panels v-model="tab" animated transition-prev="jump-up" transition-next="jump-up">
            <!-- general -->
            <q-tab-panel name="general">
              <q-card-section>
                <q-select
                  @input="site = sites[0]"
                  dense
                  outlined
                  v-model="client"
                  :options="Object.keys(tree)"
                  label="Client"
                />
              </q-card-section>
              <q-card-section>
                <q-select dense outlined v-model="site" :options="sites" label="Site" />
              </q-card-section>
              <q-card-section>
                <q-select
                  dense
                  outlined
                  v-model="monType"
                  :options="monTypes"
                  label="Monitoring mode"
                />
              </q-card-section>
              <q-card-section>
                <q-input
                  outlined
                  dense
                  v-model="desc"
                  label="Description"
                  :rules="[val => !!val || '*Required']"
                />
              </q-card-section>
              <q-card-section>
                <q-input
                  dense
                  outlined
                  v-model.number="checkInterval"
                  label="Interval for checks (seconds)"
                  :rules="[ 
                      val => !!val || '*Required',
                      val => val >= 60 || 'Minimum is 60 seconds',
                      val => val <= 3600 || 'Maximum is 3600 seconds'
                  ]"
                />
              </q-card-section>
              <q-card-section>
                <q-input
                  dense
                  outlined
                  v-model.number="overdueTime"
                  label="Send an overdue alert if the server has not reported in after (minutes)"
                  :rules="[ 
                      val => !!val || '*Required',
                      val => val >= 5 || 'Minimum is 5 minutes',
                      val => val < 9999999 || 'Maximum is 9999999 minutes'
                  ]"
                />
              </q-card-section>
              <q-card-section>
                <q-checkbox v-model="emailAlert" label="Get overdue email alerts" />
                <q-space />
                <q-checkbox v-model="textAlert" label="Get overdue text alerts" />
              </q-card-section>
            </q-tab-panel>
            <!-- patch -->
            <q-tab-panel name="patch">
              <!-- Auto Approval -->
              <div class="text-subtitle2">Auto Approval</div>
              <hr />
              <q-card-section class="row">
                <div class="col-3">Severity</div>
                <div class="col-4"></div>
                <div class="col-5">Action</div>
              </q-card-section>
              <q-card-section class="row">
                <div class="col-3">Critical:</div>
                <div class="col-4"></div>
                <q-select
                  dense
                  class="col-5"
                  outlined
                  v-model="critical"
                  :options="severityOptions"
                  emit-value
                  map-options
                />
              </q-card-section>
              <q-card-section class="row">
                <div class="col-3">Important:</div>
                <div class="col-4"></div>
                <q-select
                  dense
                  class="col-5"
                  outlined
                  v-model="important"
                  :options="severityOptions"
                  emit-value
                  map-options
                />
              </q-card-section>
              <q-card-section class="row">
                <div class="col-3">Moderate:</div>
                <div class="col-4"></div>
                <q-select
                  dense
                  class="col-5"
                  outlined
                  v-model="moderate"
                  :options="severityOptions"
                  emit-value
                  map-options
                />
              </q-card-section>
              <q-card-section class="row">
                <div class="col-3">Low:</div>
                <div class="col-4"></div>
                <q-select
                  dense
                  class="col-5"
                  outlined
                  v-model="low"
                  :options="severityOptions"
                  emit-value
                  map-options
                />
              </q-card-section>
              <q-card-section class="row">
                <div class="col-3">Other:</div>
                <div class="col-4"></div>
                <q-select
                  dense
                  class="col-5"
                  outlined
                  v-model="other"
                  :options="severityOptions"
                  emit-value
                  map-options
                />
              </q-card-section>
              <!-- Installation Schedule -->
              <div class="text-subtitle2">Installation Schedule</div>
              <hr />
              <q-card-section class="row">
                <div class="col-3">Scheduled Time:</div>
                <div class="col-4"></div>
                <q-select
                  dense
                  class="col-5"
                  outlined
                  v-model="scheduledTime"
                  :options="timeOptions"
                  emit-value
                  map-options
                />
              </q-card-section>
              <q-card-section>
                <div class="q-gutter-sm">
                  <q-checkbox v-model="dayOptions" :val="0" label="Monday" />
                  <q-checkbox v-model="dayOptions" :val="1" label="Tuesday" />
                  <q-checkbox v-model="dayOptions" :val="2" label="Wednesday" />
                  <q-checkbox v-model="dayOptions" :val="3" label="Thursday" />
                  <q-checkbox v-model="dayOptions" :val="4" label="Friday" />
                  <q-checkbox v-model="dayOptions" :val="5" label="Saturday" />
                  <q-checkbox v-model="dayOptions" :val="6" label="Sunday" />
                </div>
              </q-card-section>
              <!-- Reboot After Installation -->
              <div class="text-subtitle2">Reboot After Installation</div>
              <hr />
              <q-card-section class="row">
                <div class="q-gutter-sm">
                  <q-radio v-model="rebootAfterInstall" val="never" label="Never" />
                  <q-radio v-model="rebootAfterInstall" val="required" label="When Required" />
                  <q-radio v-model="rebootAfterInstall" val="always" label="Always" />
                </div>
              </q-card-section>
              <!-- Failed Patches -->
              <div class="text-subtitle2">Failed Patches</div>
              <hr />
              <q-card-section class="row">
                <div class="col-5">
                  <q-checkbox v-model="reprocessFailed" label="Reprocess failed patches" />
                </div>

                <div class="col-3">
                  <q-input
                    dense
                    v-model.number="reprocessFailedTimes"
                    type="number"
                    filled
                    label="Times"
                    :rules="[ val => val > 0 || 'Must be greater than 0']"
                  />
                </div>
                <div class="col-3"></div>
                <q-checkbox
                  v-model="emailIfFail"
                  label="Send an email when patch installation fails"
                />
              </q-card-section>
            </q-tab-panel>
          </q-tab-panels>
          <q-card-section class="row items-center">
            <q-btn label="Save" color="primary" type="submit" />
            <q-btn label="Cancel" v-close-popup />
          </q-card-section>
        </q-form>
      </template>
    </q-splitter>
  </q-card>
</template>

<script>
import axios from "axios";
import { mapGetters } from "vuex";
import mixins from "@/mixins/mixins";
import { scheduledTimes } from "@/mixins/data";
export default {
  name: "EditAgent",
  mixins: [mixins],
  data() {
    return {
      pk: null,
      hostname: "",
      client: "",
      site: "",
      monType: "",
      monTypes: ["server", "workstation"],
      desc: "",
      overdueTime: null,
      checkInterval: null,
      emailAlert: null,
      textAlert: null,
      tree: {},
      updatePolicy: [],
      splitterModel: 15,
      tab: "general",
      severityOptions: [
        { label: "Manual", value: "manual" },
        { label: "Approve", value: "approve" },
        { label: "Ignore", value: "ignore" }
      ],
      timeOptions: scheduledTimes,
      dayOptions: [],
      scheduledTime: null,
      rebootAfterInstall: null,
      reprocessFailed: null,
      reprocessFailedTimes: null,
      emailIfFail: null,
      critical: null,
      important: null,
      moderate: null,
      low: null,
      other: null
    };
  },
  methods: {
    getAgentInfo() {
      axios.get(`/agents/${this.selectedAgentPk}/agentdetail/`).then(r => {
        this.pk = r.data.id;
        this.hostname = r.data.hostname;
        this.client = r.data.client;
        this.site = r.data.site;
        this.monType = r.data.monitoring_type;
        this.desc = r.data.description;
        this.overdueTime = r.data.overdue_time;
        this.checkInterval = r.data.check_interval;
        this.emailAlert = r.data.overdue_email_alert;
        this.textAlert = r.data.overdue_text_alert;
        this.updatePolicy = r.data.winupdatepolicy;
        this.critical = r.data.winupdatepolicy[0].critical;
        this.important = r.data.winupdatepolicy[0].important;
        this.moderate = r.data.winupdatepolicy[0].moderate;
        this.low = r.data.winupdatepolicy[0].low;
        this.other = r.data.winupdatepolicy[0].other;
        this.scheduledTime = r.data.winupdatepolicy[0].run_time_hour;
        this.dayOptions = r.data.winupdatepolicy[0].run_time_days;
        this.rebootAfterInstall =
          r.data.winupdatepolicy[0].reboot_after_install;
        this.reprocessFailed = r.data.winupdatepolicy[0].reprocess_failed;
        this.reprocessFailedTimes =
          r.data.winupdatepolicy[0].reprocess_failed_times;
        this.emailIfFail = r.data.winupdatepolicy[0].email_if_fail;
      });
    },
    getClientsSites() {
      axios.get("/clients/loadclients/").then(r => (this.tree = r.data));
    },
    editAgent() {
      const data = {
        pk: this.pk,
        client: this.client,
        site: this.site,
        montype: this.monType,
        desc: this.desc,
        overduetime: this.overdueTime,
        checkinterval: this.checkInterval,
        emailalert: this.emailAlert,
        textalert: this.textAlert,
        critical: this.critical,
        important: this.important,
        moderate: this.moderate,
        low: this.low,
        other: this.other,
        scheduledtime: this.scheduledTime,
        dayoptions: this.dayOptions,
        rebootafterinstall: this.rebootAfterInstall,
        reprocessfailed: this.reprocessFailed,
        reprocessfailedtimes: this.reprocessFailedTimes,
        emailiffail: this.emailIfFail
      };
      axios
        .patch("/agents/editagent/", data)
        .then(r => {
          this.$emit("close");
          this.$emit("edited");
          this.notifySuccess("Agent was edited!");
        })
        .catch(e => this.notifyError(e.response.data.error));
    }
  },
  computed: {
    ...mapGetters(["selectedAgentPk"]),
    sites() {
      return this.tree[this.client];
    }
  },
  created() {
    this.getAgentInfo();
    this.getClientsSites();
  }
};
</script>