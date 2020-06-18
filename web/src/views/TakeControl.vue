<template>
  <iframe
    style="overflow:hidden;height:900px;"
    :src="takeControlUrl"
    width="100%"
    height="100%"
    scrolling="no"
  ></iframe>
</template>

<script>
import axios from "axios";

export default {
  name: "TakeControl",
  data() {
    return {
      takeControlUrl: ""
    };
  },
  methods: {
    genURL() {
      const pk = this.$route.params.pk;
      axios.get(`/agents/${pk}/takecontrol/`).then(r => (this.takeControlUrl = r.data));
    }
  },
  created() {
    this.genURL();
  }
};
</script>