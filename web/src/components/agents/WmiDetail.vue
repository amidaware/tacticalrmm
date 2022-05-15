<template>
  <div class="scroll" :style="{ 'max-height': tabHeight - 10 }">
    <div v-for="i in info" :key="i + uid()">
      <div v-for="j in i" :key="j + uid()">
        <div v-for="(v, k) in j" :key="v + uid()">
          <span class="text-overline">{{ k }}:</span>
          <q-badge color="primary" class="q-ml-sm text-caption">{{
            v
          }}</q-badge>
        </div>
      </div>
      <q-separator v-if="info.length > 1" />
    </div>
  </div>
</template>

<script>
// composition imports
import { computed } from "vue";
import { useStore } from "vuex";
import { uid } from "quasar";

export default {
  name: "WmiDetail",
  props: { info: !Object },
  setup() {
    // setup vuex
    const store = useStore();
    const tabHeight = computed(() => store.state.tabHeight);

    return {
      tabHeight,
      uid,
    };
  },
};
</script>
