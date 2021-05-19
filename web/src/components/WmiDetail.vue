<template>
  <div class="scroll" :style="{ 'max-height': tabsTableHeight }">
    <div v-for="i in info">
      <div v-for="j in i">
        <div v-for="(v, k) in j">
          <span class="text-overline">{{ k }}:</span>
          <q-badge color="primary" class="q-ml-sm text-caption">{{ v }}</q-badge>
        </div>
      </div>
      <hr v-if="info.length > 1" />
    </div>
  </div>
</template>

<script>
import { mapGetters } from "vuex";

export default {
  name: "WmiDetail",
  props: ["info"],
  computed: {
    ...mapGetters(["tabsTableHeight"]),
  },
};
</script>

