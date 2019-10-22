<template>
  <div></div>
</template>

<script>
export default {
  name: "Logout",
  mounted() {
    this.$store.dispatch("destroyToken").then(response => {
      this.$router.push({ name: "Login" });
    });
  }
};
</script>