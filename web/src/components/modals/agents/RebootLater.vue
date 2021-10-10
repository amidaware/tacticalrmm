<template>
  <q-card style="min-width: 400px" class="q-pa-xs">
    <q-card-section>
      <div class="row items-center">
        <div class="text-h6">Schedule a reboot</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </div>
    </q-card-section>
    <q-card-section>
      <q-input filled v-model="datetime">
        <template v-slot:prepend>
          <q-icon name="event" class="cursor-pointer">
            <q-popup-proxy transition-show="scale" transition-hide="scale">
              <q-date v-model="datetime" mask="YYYY-MM-DD HH:mm" />
            </q-popup-proxy>
          </q-icon>
        </template>

        <template v-slot:append>
          <q-icon name="access_time" class="cursor-pointer">
            <q-popup-proxy transition-show="scale" transition-hide="scale">
              <q-time v-model="datetime" mask="YYYY-MM-DD HH:mm" />
            </q-popup-proxy>
          </q-icon>
        </template>
      </q-input>
    </q-card-section>
    <q-card-actions align="left">
      <q-btn dense label="Schedule Reboot" color="primary" @click="scheduleReboot" />
    </q-card-actions>
  </q-card>
</template>

<script>
import { mapGetters } from "vuex";
import mixins from "@/mixins/mixins";
import { date } from "quasar";

export default {
  name: "RebootLater",
  mixins: [mixins],
  data() {
    return {
      datetime: null,
    };
  },
  methods: {
    scheduleReboot() {
      this.$q.loading.show({ message: "Contacting agent..." });
      const data = { pk: this.selectedAgentId, datetime: this.datetime };
      this.$axios
        .patch(`/agents/${this.selectedAgentId}reboot/`, data)
        .then(r => {
          this.$q.loading.hide();
          this.$emit("close");
          this.$emit("edited");
          this.confirmReboot(r.data);
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
    getCurrentDate() {
      let timeStamp = Date.now();
      this.datetime = date.formatDate(timeStamp, "YYYY-MM-DD HH:mm");
    },
    confirmReboot(data) {
      this.$q.dialog({
        title: "Reboot pending",
        style: "width: 40vw",
        message: `A reboot has been scheduled for <strong>${data.time}</strong> on ${data.agent}.
          <br />It can be cancelled from the Pending Actions menu until the scheduled time.`,
        html: true,
      });
    },
  },
  computed: {
    ...mapGetters(["selectedAgentId"]),
  },
  mounted() {
    this.getCurrentDate();
  },
};
</script>