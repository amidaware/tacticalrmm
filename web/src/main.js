import Vue from "vue";
import App from "./App.vue";
import router from "./router";
import axios from "axios";
import { store } from "./store/store";
import "./quasar";

Vue.config.productionTip = false;

axios.defaults.baseURL =
  process.env.NODE_ENV === "production"
    ? process.env.VUE_APP_PROD_URL
    : process.env.VUE_APP_DEV_URL;

router.beforeEach((to, from, next) => {
  if (to.meta.requireAuth) {
    if (!store.getters.loggedIn) {
      next({
        name: "Login"
      });
    } else {
      next();
    }
  } else if (to.meta.requiresVisitor) {
    if (store.getters.loggedIn) {
      next({
        name: "Dashboard"
      });
    } else {
      next();
    }
  } else {
    next();
  }
});

axios.interceptors.request.use(
  function (config) {
    const token = store.state.token;

    if (token != null) {
      config.headers.Authorization = `Token ${token}`;
    }

    return config;
  },
  function (err) {
    return Promise.reject(err);
  }
);

axios.interceptors.response.use(
  function (response) {
    if (response.status === 400) {
      return Promise.reject(response);
    }
    return response;
  },
  function (error) {
    if (error.response.status === 401) {
      router.push({ path: "/expired" });
    }
    return Promise.reject(error);
  }
);

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount("#app");
