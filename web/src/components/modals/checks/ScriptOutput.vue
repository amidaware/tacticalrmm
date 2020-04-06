<template>
  <q-card style="min-width: 700px" class="q-pa-xs">
    <q-card-section>
      <div class="row items-center">
        <div class="text-h6">{{ scriptInfo.script.name }}</div>
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
      <div v-if="scriptInfo.stdout">
        Standard Output:
        <q-scroll-area style="height: 200px; max-height: 500px;">
          <pre>{{ scriptInfo.stdout }}</pre>
        </q-scroll-area>
      </div>
      <div v-if="scriptInfo.stderr">
        Standard Error:
        <q-scroll-area style="height: 200px; max-height: 500px;">
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
  }
};
</script>