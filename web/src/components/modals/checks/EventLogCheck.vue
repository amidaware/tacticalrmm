<template>
  <q-card style="min-width: 40vw">
    <q-card-section class="row items-center">
      <div v-if="mode === 'add'" class="text-h6">Add Event Log Check</div>
      <div v-else-if="mode === 'edit'" class="text-h6">Edit Event Log Check</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>

    <q-form @submit.prevent="mode === 'add' ? addCheck() : editCheck()">
      <q-card-section>
        <q-input
          dense
          outlined
          v-model="eventlogcheck.name"
          label="Descriptive Name"
          :rules="[ val => !!val || '*Required' ]"
        />
      </q-card-section>
      <q-card-section>
        <q-select
          dense
          outlined
          v-model="eventlogcheck.log_name"
          :options="logNameOptions"
          label="Event log to query"
        />
      </q-card-section>
      <q-card-section>
        <q-select
          dense
          outlined
          v-model="eventlogcheck.fail_when"
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
          v-model="eventlogcheck.event_id"
          label="Event ID (Use * to match every event ID)"
          :rules="[val => validateEventID(val) || 'Invalid Event ID']"
        />
      </q-card-section>
      <q-card-section>
        <q-input
          dense
          outlined
          v-model.number="eventlogcheck.search_last_days"
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
          <q-radio dense v-model="eventlogcheck.event_type" val="INFO" label="Information" />
          <q-radio dense v-model="eventlogcheck.event_type" val="WARNING" label="Warning" />
          <q-radio dense v-model="eventlogcheck.event_type" val="ERROR" label="Error" />
          <q-radio
            dense
            v-model="eventlogcheck.event_type"
            val="AUDIT_SUCCESS"
            label="Success Audit"
          />
          <q-radio
            dense
            v-model="eventlogcheck.event_type"
            val="AUDIT_FAILURE"
            label="Failure Audit"
          />
        </div>
      </q-card-section>
      <q-card-section>
        <q-select
          outlined
          dense
          v-model="eventlogcheck.fails_b4_alert"
          :options="failOptions"
          label="Number of consecutive failures before alert"
        />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn v-if="mode === 'add'" label="Add" color="primary" type="submit" />
        <q-btn v-else-if="mode === 'edit'" label="Edit" color="primary" type="submit" />
        <q-btn label="Cancel" v-close-popup />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
export default {
  name: "EventLogCheck",
  props: {
    agentpk: Number,
    policypk: Number,
    mode: String,
    checkpk: Number,
  },
  mixins: [mixins],
  data() {
    return {
      eventlogcheck: {
        check_type: "eventlog",
        log_name: "Application",
        event_id: null,
        event_type: "INFO",
        fail_when: "contains",
        search_last_days: 1,
        fails_b4_alert: 1,
        event_id_is_wildcard: false,
      },
      logNameOptions: ["Application", "System", "Security"],
      failWhenOptions: [
        { label: "Log contains", value: "contains" },
        { label: "Log does not contain", value: "not_contains" },
      ],
      failOptions: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    };
  },
  methods: {
    getCheck() {
      axios.get(`/checks/${this.checkpk}/check/`).then(r => {
        this.eventlogcheck = r.data;
        if (r.data.check_type === "eventlog" && r.data.event_id_is_wildcard) {
          this.eventlogcheck.event_id = "*";
        }
      });
    },
    addCheck() {
      const pk = this.policypk ? { policy: this.policypk } : { pk: this.agentpk };
      this.eventlogcheck.event_id_is_wildcard = this.eventlogcheck.event_id === "*" ? true : false;
      const data = {
        ...pk,
        check: this.eventlogcheck,
      };
      axios
        .post("/checks/checks/", data)
        .then(r => {
          this.$emit("close");
          this.reloadChecks();
          this.notifySuccess(r.data);
        })
        .catch(e => this.notifyError(e.response.data.non_field_errors));
    },
    editCheck() {
      this.eventlogcheck.event_id_is_wildcard = this.eventlogcheck.event_id === "*" ? true : false;
      axios
        .patch(`/checks/${this.checkpk}/check/`, this.eventlogcheck)
        .then(r => {
          this.$emit("close");
          this.reloadChecks();
          this.notifySuccess(r.data);
        })
        .catch(e => this.notifyError(e.response.data.non_field_errors));
    },
    reloadChecks() {
      if (this.policypk) {
        this.$store.dispatch("automation/loadPolicyChecks", this.policypk);
      } else {
        this.$store.dispatch("loadChecks", this.agentpk);
      }
    },
    validateEventID(val) {
      if (val === null || val.toString().replace(/\s/g, "") === "") {
        return false;
      } else if (val === "*") {
        return true;
      } else if (!isNaN(val)) {
        return true;
      } else {
        return false;
      }
    },
  },
  mounted() {
    if (this.mode === "edit") {
      this.getCheck();
    }
  },
};
</script>