import Vue from 'vue';
import axios from 'axios';

export default function ({ router, store }) {

  Vue.prototype.$axios = axios;

  let getBaseUrl = () => {
    if (process.env.NODE_ENV === "production") {
      if (process.env.DOCKER_BUILD) {
        return window._env_.PROD_URL;
      } else {
        return process.env.PROD_API;
      }
    } else {
      return process.env.DEV_API;
    }
  };

  axios.interceptors.request.use(
    function (config) {
      config.baseURL = getBaseUrl()
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
}

