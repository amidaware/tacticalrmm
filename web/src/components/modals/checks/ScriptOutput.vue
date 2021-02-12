<template>
  <q-dialog ref="dialog" @hide="onHide">
    <q-card class="q-dialog-plugin q-pa-xs" style="min-width: 70vw">
      <q-bar>
        {{ scriptInfo.readable_desc }}
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <q-card-section>
        <div>
          Last Run:
          <code>{{ scriptInfo.last_run }}</code>
          <br />Run Time:
          <code>{{ scriptInfo.execution_time }} seconds</code>
          <br />Return Code:
          <code>{{ scriptInfo.retcode }}</code>
          <br />
        </div>
        <br />
        <div v-if="scriptInfo.stdout">
          Standard Output
          <q-separator />
          <q-scroll-area style="height: 50vh; max-height: 70vh">
            <pre>{{ scriptInfo.stdout }}</pre>
          </q-scroll-area>
        </div>
        <div v-if="scriptInfo.stderr">
          Standard Error:
          <q-scroll-area style="height: 50vh; max-height: 70vh">
            <pre>{{ scriptInfo.stderr }}</pre>
          </q-scroll-area>
        </div>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script>
export default {
  name: "ScriptOutput",
  props: ["scriptInfo"],
  methods: {
    show() {
      this.$refs.dialog.show();
    },
    hide() {
      this.$refs.dialog.hide();
    },
    onHide() {
      this.$emit("hide");
    },
  },
};
</script>