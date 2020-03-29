<template>
  <q-card style="min-width: 800px" v-if="agentLoaded && clientsLoaded">
    <q-splitter v-model="splitterModel">
      <template v-slot:before>
        <q-tabs dense v-model="tab" vertical class="text-primary">
          <q-tab name="general" label="General" />
          <q-tab name="patch" label="Patches" />
        </q-tabs>
      </template>
      <template v-slot:after>
        <q-form @submit.prevent="editAgent">
          <q-card-section class="row items-center">
            <div class="text-h6">Edit {{ agent.hostname }}</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </q-card-section>
          <q-scroll-area :thumb-style="thumbStyle" style="height: 500px;">
            <q-tab-panels
              v-model="tab"
              animated
              transition-prev="jump-up"
              transition-next="jump-up"
            >
              <!-- general -->
              <q-tab-panel name="general">
                <q-card-section class="row">
                  <div class="col-2">Client:</div>
                  <div class="col-2"></div>
                  <q-select
                    @input="agent.site = sites[0]"
                    dense
                    outlined
                    v-model="agent.client"
                    :options="Object.keys(tree)"
                    class="col-8"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">Site:</div>
                  <div class="col-2"></div>
                  <q-select class="col-8" dense outlined v-model="agent.site" :options="sites" />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">Type:</div>
                  <div class="col-2"></div>
                  <q-select
                    dense
                    outlined
                    v-model="agent.monitoring_type"
                    :options="monTypes"
                    class="col-8"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">Description:</div>
                  <div class="col-2"></div>
                  <q-input
                    outlined
                    dense
                    v-model="agent.description"
                    class="col-8"
                    :rules="[val => !!val || '*Required']"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-10">Check interval:</div>
                  <q-input
                    dense
                    type="number"
                    filled
                    label="Seconds"
                    v-model.number="agent.check_interval"
                    class="col-2"
                    :rules="[ 
                      val => !!val || '*Required',
                      val => val >= 60 || 'Minimum is 60 seconds',
                      val => val <= 3600 || 'Maximum is 3600 seconds'
                  ]"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div
                    class="col-10"
                  >Send an overdue alert if the server has not reported in after:</div>
                  <q-input
                    dense
                    type="number"
                    filled
                    label="Minutes"
                    v-model.number="agent.overdue_time"
                    class="col-2"
                    :rules="[ 
                      val => !!val || '*Required',
                      val => val >= 5 || 'Minimum is 5 minutes',
                      val => val < 9999999 || 'Maximum is 9999999 minutes'
                  ]"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <q-checkbox v-model="agent.overdue_email_alert" label="Get overdue email alerts" />
                  <q-checkbox v-model="agent.overdue_text_alert" label="Get overdue sms alerts" />
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
                    v-model="agent.winupdatepolicy[0].critical"
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
                    v-model="agent.winupdatepolicy[0].important"
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
                    v-model="agent.winupdatepolicy[0].moderate"
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
                    v-model="agent.winupdatepolicy[0].low"
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
                    v-model="agent.winupdatepolicy[0].other"
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
                    v-model="agent.winupdatepolicy[0].run_time_hour"
                    :options="timeOptions"
                    emit-value
                    map-options
                  />
                </q-card-section>
                <q-card-section>
                  <div class="q-gutter-sm">
                    <q-checkbox
                      v-model="agent.winupdatepolicy[0].run_time_days"
                      :val="0"
                      label="Monday"
                    />
                    <q-checkbox
                      v-model="agent.winupdatepolicy[0].run_time_days"
                      :val="1"
                      label="Tuesday"
                    />
                    <q-checkbox
                      v-model="agent.winupdatepolicy[0].run_time_days"
                      :val="2"
                      label="Wednesday"
                    />
                    <q-checkbox
                      v-model="agent.winupdatepolicy[0].run_time_days"
                      :val="3"
                      label="Thursday"
                    />
                    <q-checkbox
                      v-model="agent.winupdatepolicy[0].run_time_days"
                      :val="4"
                      label="Friday"
                    />
                    <q-checkbox
                      v-model="agent.winupdatepolicy[0].run_time_days"
                      :val="5"
                      label="Saturday"
                    />
                    <q-checkbox
                      v-model="agent.winupdatepolicy[0].run_time_days"
                      :val="6"
                      label="Sunday"
                    />
                  </div>
                </q-card-section>
                <!-- Reboot After Installation -->
                <div class="text-subtitle2">Reboot After Installation</div>
                <hr />
                <q-card-section class="row">
                  <div class="q-gutter-sm">
                    <q-radio
                      v-model="agent.winupdatepolicy[0].reboot_after_install"
                      val="never"
                      label="Never"
                    />
                    <q-radio
                      v-model="agent.winupdatepolicy[0].reboot_after_install"
                      val="required"
                      label="When Required"
                    />
                    <q-radio
                      v-model="agent.winupdatepolicy[0].reboot_after_install"
                      val="always"
                      label="Always"
                    />
                  </div>
                </q-card-section>
                <!-- Failed Patches -->
                <div class="text-subtitle2">Failed Patches</div>
                <hr />
                <q-card-section class="row">
                  <div class="col-5">
                    <q-checkbox
                      v-model="agent.winupdatepolicy[0].reprocess_failed"
                      label="Reprocess failed patches"
                    />
                  </div>

                  <div class="col-3">
                    <q-input
                      dense
                      v-model.number="agent.winupdatepolicy[0].reprocess_failed_times"
                      type="number"
                      filled
                      label="Times"
                      :rules="[ val => val > 0 || 'Must be greater than 0']"
                    />
                  </div>
                  <div class="col-3"></div>
                  <q-checkbox
                    v-model="agent.winupdatepolicy[0].email_if_fail"
                    label="Send an email when patch installation fails"
                  />
                </q-card-section>
              </q-tab-panel>
            </q-tab-panels>
          </q-scroll-area>
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
      agentLoaded: false,
      clientsLoaded: false,
      agent: {},
      monTypes: ["server", "workstation"],
      tree: {},
      splitterModel: 15,
      tab: "general",
      severityOptions: [
        { label: "Manual", value: "manual" },
        { label: "Approve", value: "approve" },
        { label: "Ignore", value: "ignore" }
      ],
      timeOptions: scheduledTimes,
      thumbStyle: {
        right: "2px",
        borderRadius: "5px",
        backgroundColor: "#027be3",
        width: "5px",
        opacity: 0.75
      }
    };
  },
  methods: {
    getAgentInfo() {
      axios.get(`/agents/${this.selectedAgentPk}/agentdetail/`).then(r => {
        this.agent = r.data;
        this.agentLoaded = true;
      });
    },
    getClientsSites() {
      axios.get("/clients/loadclients/").then(r => {
        this.tree = r.data;
        this.clientsLoaded = true;
      });
    },
    editAgent() {
      let data = this.agent;
      delete data.services;
      delete data.wmi_detail;
      delete data.disks;
      delete data.local_ip;

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
      if (this.agentLoaded && this.clientsLoaded) {
        return this.tree[this.agent.client];
      }
    }
  },
  created() {
    this.getAgentInfo();
    this.getClientsSites();
  }
};
</script>