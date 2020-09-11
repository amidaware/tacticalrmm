<template>
  <iframe
    style="overflow:hidden;height:900px;"
    :src="control"
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
      control: "",
    };
  },
  methods: {
    genURL() {
      const pk = this.$route.params.pk;
      axios.get(`/agents/${pk}/meshcentral/`).then(r => (this.control = r.data.control));
    },
  },
  created() {
    this.genURL();
  },
};
</script>