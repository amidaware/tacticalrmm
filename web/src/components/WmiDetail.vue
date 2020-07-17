<template>
  <div class="scroll" style="max-height: 32vh">
    <div v-for="i in info" :key="i + randomID()">
      <div v-for="j in i" :key="j + randomID()">
        <div v-for="(v, k) in j" :key="v + randomID()">
          <span class="text-overline">{{ k }}:</span>
          <q-badge color="primary" class="q-ml-sm text-caption">{{ v }}</q-badge>
        </div>
      </div>
      <hr v-if="info.length > 1" />
    </div>
  </div>
</template>

<script>
import { uid } from "quasar";

export default {
  name: "WmiDetail",
  props: ["info"],
  methods: {
    randomID() {
      return uid();
    }
  }
};
</script>

