<template>
  <q-card style="min-width: 400px">
    <q-card-section class="row">
      <q-card-actions align="left">
        <div class="text-h6">Server Maintenance</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section>
      <q-form @submit.prevent="submit">
        <q-card-section>
          <q-select
            :rules="[val => !!val || '*Required']"
            outlined
            options-dense
            label="Actions"
            v-model="action"
            :options="actions"
            emit-value
            map-options
            @input="clear"
          />
        </q-card-section>

        <q-card-section v-if="action === 'prune_db'">
          <q-checkbox v-model="prune_tables" val="audit_logs" label="Audit Log">
            <q-tooltip>Removes agent check results</q-tooltip>
          </q-checkbox>
          <q-checkbox v-model="prune_tables" val="pending_actions" label="Pending Actions">
            <q-tooltip>Removes completed pending actions</q-tooltip>
          </q-checkbox>
          <q-checkbox v-model="prune_tables" val="alerts" label="Alerts">
            <q-tooltip>Removes all alerts</q-tooltip>
          </q-checkbox>
        </q-card-section>

        <q-card-actions align="left">
          <q-btn label="Submit" color="primary" type="submit" class="full-width" />
        </q-card-actions>
      </q-form>
    </q-card-section>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "ServerMaintenance",
  mixins: [mixins],
  data() {
    return {
      action: null,
      prune_tables: [],
      actions: [
        {
          label: "Reload Nats Configuration",
          value: "reload_nats",
        },
        {
          label: "Remove Orphaned Tasks",
          value: "rm_orphaned_tasks",
        },
        {
          label: "Prune DB Tables",
          value: "prune_db",
        },
      ],
    };
  },
  methods: {
    clear() {
      this.prune_tables = [];
    },
    submit() {
      this.$q.loading.show();

      let data = {
        action: this.action,
        prune_tables: this.prune_tables,
      };

      this.$axios
        .post("core/servermaintenance/", data)
        .then(r => {
          this.$q.loading.hide();
          this.notifySuccess(r.data);
        })
        .catch(e => {
          this.$q.loading.hide();
        });
    },
  },
};
</script>