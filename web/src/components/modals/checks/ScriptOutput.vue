<template>
  <q-card style="min-width: 70vw" class="q-pa-xs">
    <q-card-section>
      <div class="row items-center">
        <div class="text-h6">{{ scriptInfo.readable_desc }}</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </div>
      <div>
        Last Run:
        <code>{{ scriptInfo.last_run }}</code>
        <br />Run Time:
        <code>{{ scriptInfo.execution_time}} seconds</code>
        <br />Return Code:
        <code>{{ scriptInfo.retcode }}</code>
        <br />
      </div>
      <br />
      <div v-if="scriptInfo.stdout">
        Standard Output
        <q-separator />
        <q-scroll-area style="height: 50vh; max-height: 70vh;">
          <pre>{{ scriptInfo.stdout }}</pre>
        </q-scroll-area>
      </div>
      <div v-if="scriptInfo.stderr">
        Standard Error:
        <q-scroll-area style="height: 50vh; max-height: 70vh;">
          <pre>{{ scriptInfo.stderr }}</pre>
        </q-scroll-area>
      </div>
    </q-card-section>
  </q-card>
</template>

<script>
export default {
  name: "ScriptOutput",
  props: ["scriptInfo"],
  beforeDestroy() {
    this.$emit("close");
  },
};
</script>