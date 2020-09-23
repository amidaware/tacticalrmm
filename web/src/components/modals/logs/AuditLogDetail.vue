<template>
  <q-card style="width: 900px; max-width: 90vw;">
    <q-bar>
      {{ log.message }}
      <q-space />
      <q-btn dense flat icon="close" v-close-popup />
    </q-bar>
    <q-card-section class="row">
      <div class="col-6">
        <div class="text-h6">Before</div>
        <pre>{{ JSON.stringify(log.before_value, null, 4) }}</pre>
      </div>

      <div class="col-6">
        <div class="text-h6">After</div>
        <pre>{{ JSON.stringify(log.after_value, null, 4) }}</pre>
      </div>
    </q-card-section>
  </q-card>
</template>
<script>
export default {
  name: "AuditLogDetail",
  props: {
    log: Object,
  },
  data() {
    return {};
  },
};
</script>