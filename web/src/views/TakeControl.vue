<template>
  <div class="q-pa-none q-ma-none">
    <div class="row q-pb-xs q-pl-md">
      <span class="text-caption">
        Agent Status:
        <q-badge :color="statusColor" :label="status" />
      </span>
      <q-space />
      <q-btn class="q-mr-md" color="primary" size="sm" label="Restart Connection" icon="refresh" @click="restart" />
      <q-btn color="negative" size="sm" label="Recover Connection" icon="fas fa-first-aid" @click="repair" />
      <q-space />
    </div>

    <q-video v-show="visible" :ratio="16 / 9" :src="control"></q-video>
  </div>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "TakeControl",
  mixins: [mixins],
  data() {
    return {
      control: "",
      visible: true,
      status: null,
      title: "",
    };
  },
  computed: {
    statusColor() {
      if (this.status !== null) {
        let color;
        switch (this.status) {
          case "online":
            color = "positive";
            break;
          case "offline":
            color = "warning";
            break;
          case "overdue":
            color = "negative";
            break;
        }
        return color;
      }
    },
  },
  meta() {
    return {
      title: this.title,
    };
  },
  methods: {
    genURL() {
      this.$q.loading.show();
      this.visible = false;
      this.$axios
        .get(`/agents/${this.$route.params.pk}/meshcentral/`)
        .then(r => {
          this.title = `${r.data.hostname} - ${r.data.client} - ${r.data.site} | Take Control`;
          this.control = r.data.control;
          this.status = r.data.status;
          this.$q.loading.hide();
          this.visible = true;
        })
        .catch(e => {
          this.visible = true;
          this.$q.loading.hide();
          this.notifyError("Something went wrong");
        });
    },
    restart() {
      this.visible = false;
      this.$q.loading.show({ message: "Restarting Mesh Agent" });
      const data = {
        pk: this.$route.params.pk,
        sv_name: "mesh agent",
        sv_action: "restart",
      };

      this.$axios
        .post("/services/serviceaction/", data)
        .then(r => {
          setTimeout(() => {
            this.visible = true;
            this.$q.loading.hide();
            this.notifySuccess("Mesh agent service was restarted");
          }, 500);
        })
        .catch(e => {
          this.visible = true;
          this.$q.loading.hide();
          this.notifyError(e.response.data);
        });
    },
    repair() {
      this.visible = false;
      this.$q.loading.show({ message: "Attempting to repair Mesh Agent" });
      this.$axios
        .get(`/agents/${this.$route.params.pk}/recovermesh/`)
        .then(r => {
          setTimeout(() => {
            this.visible = true;
            this.$q.loading.hide();
            this.notifySuccess(r.data);
            this.genURL();
          }, 500);
        })
        .catch(e => {
          this.visible = true;
          this.$q.loading.hide();
          this.notifyError(e.response.data);
        });
    },
  },
  created() {
    this.genURL();
  },
};
</script>