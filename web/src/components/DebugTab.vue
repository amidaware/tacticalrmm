<template>
  <div />
</template>

<script>
import { mapGetters } from "vuex";

export default {
  name: "DebugTab",
  computed: {
    ...mapGetters(["selectedAgentPk"]),
  },
};
</script>