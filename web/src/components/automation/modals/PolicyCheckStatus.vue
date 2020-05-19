<template>
  <q-card style="width: 60vw" >
    <q-card-section class="row items-center">
      <div class="text-h6">Policy Name Status</div>
      <div class="text-subtitle1">{{ this.check.desc }}</div>
      <q-space />
      <q-btn icon="close" flat round dense v-close-popup />
    </q-card-section>
    <q-card-section>
    <q-list bordered separator>
      <q-item>
        <q-item-section>Single line item</q-item-section>
      </q-item>
    </q-list>
    </q-card-section>
  </q-card>
</template>

<script>
export default {
  name: "PolicyCheckStatus",
  props: {
    check: {
      required: true,
      type: Object
    }
  },
  data() {
    return {
    }
  },
}
</script>