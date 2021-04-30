import Vue from 'vue';
import axios from 'axios';
import { Notify } from "quasar"

export const getBaseUrl = () => {
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

export default function ({ router, store }) {

  Vue.prototype.$axios = axios;

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
      return response;
    },
    function (error) {
      let text

      if (!error.response) {
        text = error.message
      }

      // unauthorized
      else if (error.response.status === 401) {
        router.push({ path: "/expired" });
      }
      else if (error.response.status === 400) {

        if (error.response.data.non_field_errors) {
          text = error.response.data.non_field_errors[0]

        } else {
          if (typeof error.response.data === "string") {
            text = error.response.data
          } else if (typeof error.response.data === "object") {
            let [key, value] = Object.entries(error.response.data)[0]
            text = key + ": " + value[0]
          }
        }

      }
      else if (error.response.status === 406) {
        text = "Missing 64 bit meshagent.exe. Upload it from File > Upload Mesh Agent"
      }
      else if (error.response.status === 415) {
        text = "Missing 32 bit meshagent-x86.exe. Upload it from File > Upload Mesh Agent"
      }

      if (text || error.response) {
        Notify.create({
          color: "negative",
          message: text ? text : "",
          caption: error.response ? error.response.status + ": " + error.response.statusText : "",
          timeout: 2500
        })
      }

      return Promise.reject({ ...error });
    }
  );
}

