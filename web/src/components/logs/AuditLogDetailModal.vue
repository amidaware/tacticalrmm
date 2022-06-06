<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="min-width: 70vw">
      <q-bar>
        {{ log.message }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup />
      </q-bar>
      <q-card-section class="scroll" style="max-height: 65vh">
        <q-splitter v-model="splitterModel">
          <template v-slot:before>
            <div class="text-h6">Before</div>
            <pre>{{ JSON.stringify(log.before_value, null, 4) }}</pre>
          </template>

          <template v-slot:after>
            <div class="text-h6">After</div>
            <pre>{{ JSON.stringify(log.after_value, null, 4) }}</pre>
          </template>
        </q-splitter>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat dense push label="Cancel" v-close-popup />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
import { useDialogPluginComponent } from "quasar";
export default {
  name: "AuditLogDetail",
  emits: [...useDialogPluginComponent.emits],
  props: {
    log: !Object,
  },
  setup() {
    const { dialogRef, onDialogHide } = useDialogPluginComponent();

    return {
      // reactive data
      splitterModel: 50,

      // quasar dialog
      dialogRef,
      onDialogHide,
    };
  },
};
</script>
