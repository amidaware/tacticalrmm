<template>
  <q-card style="min-width: 40vw">
    <q-card-section class="row items-center">
      <div class="text-h6">Add Event Log Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="addCheck">
      <q-card-section>
        <q-input
          dense
          outlined
          v-model="desc"
          label="Descriptive Name"
          :rules="[ val => !!val || '*Required' ]"
        />
      </q-card-section>
      <q-card-section>
        <q-select
          dense
          outlined
          v-model="logname"
          :options="logNameOptions"
          label="Event log to query"
        />
      </q-card-section>
      <q-card-section>
        <q-select
          dense
          outlined
          v-model="failWhen"
          :options="failWhenOptions"
          label="Fail When"
          emit-value
          map-options
        />
      </q-card-section>
      <q-card-section>
        <q-input
          dense
          outlined
          v-model.number="eventID"
          label="Event ID"
          :rules="[ 
                    val => !!val.toString() || '*Required',
                    val => val >= 0 || 'Min 0',
                    val => val <= 999999 || 'Max 999999'
                ]"
        />
      </q-card-section>
      <q-card-section>
        <q-input
          dense
          outlined
          v-model.number="searchLastDays"
          label="How many previous days to search (Enter 0 for the entire log)"
          :rules="[ 
                    val => !!val.toString() || '*Required',
                    val => val >= 0 || 'Min 0',
                    val => val <= 9999 || 'Max 9999'
                ]"
        />
      </q-card-section>
      <q-card-section>
        <span>Event Type:</span>
        <div class="q-gutter-sm">
          <q-radio dense v-model="eventType" val="INFO" label="Information" />
          <q-radio dense v-model="eventType" val="WARNING" label="Warning" />
          <q-radio dense v-model="eventType" val="ERROR" label="Error" />
          <q-radio dense v-model="eventType" val="AUDIT_SUCCESS" label="Success Audit" />
          <q-radio dense v-model="eventType" val="AUDIT_FAILURE" label="Failure Audit" />
        </div>
      </q-card-section>
      <q-card-section>
        <q-select
          outlined
          dense
          v-model="failure"
          :options="failures"
          label="Number of consecutive failures before alert"
        />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn label="Add" color="primary" type="submit" />
        <q-btn label="Cancel" v-close-popup />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import { mapState } from "vuex";
import mixins from "@/mixins/mixins";
export default {
  name: "AddEventLogCheck",
  props: ["agentpk", "policypk"],
  mixins: [mixins],
  data() {
    return {
      desc: null,
      eventID: 0,
      eventType: "INFO",
      logname: "Application",
      logNameOptions: ["Application", "System", "Security"],
      failWhen: "contains",
      searchLastDays: 1,
      failWhenOptions: [
        { label: "Log contains", value: "contains" },
        { label: "Log does not contain", value: "not_contains" }
      ],
      failure: 1,
      failures: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    };
  },
  methods: {
    addCheck() {
      const pk = this.policypk ? { policy: this.policypk } : { pk: this.agentpk };

      const data = {
        ...pk,
        check_type: "eventlog",
        desc: this.desc,
        log_name: this.logname,
        event_id: this.eventID,
        event_type: this.eventType,
        fail_when: this.failWhen,
        search_last_days: this.searchLastDays,
        failure: this.failure
      };
      axios
        .post("/checks/addstandardcheck/", data)
        .then(r => {
          this.$emit("close");

          if (this.policypk) {
            this.$store.dispatch("automation/loadPolicyChecks", this.policypk);
          } else {
            this.$store.dispatch("loadChecks", this.agentpk);
          }

          this.notifySuccess("Event log check was added!");
        })
        .catch(e => this.notifyError(e.response.data.desc));
    }
  }
};
</script>