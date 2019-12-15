<template>
  <div class="fixed-center text-center">
    <p class="text-faded">Your session has expired</p>
    <q-btn color="secondary" style="width:200px;" @click="$router.push('/')">Login</q-btn>
  </div>
</template>

<script>
export default {
  name: "SessionExpired",
  created() {
    this.$store.dispatch("destroyToken");
  },
  mounted() {
    if (localStorage.getItem("reloaded")) {
      localStorage.removeItem("reloaded");
    } else {
      localStorage.setItem("reloaded", "1");
      location.reload();
    }
  }
};
</script>