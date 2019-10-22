import Vue from "vue";

import "./styles/quasar.styl";
import "@quasar/extras/material-icons/material-icons.css";
import "@quasar/extras/fontawesome-v5/fontawesome-v5.css";
import "@quasar/extras/mdi-v3/mdi-v3.css";
import Quasar from "quasar";

Vue.use(Quasar, {
  config: {
    loadingBar: {
      color: "red",
      size: "4px"
    },
    notify: {
      position: "top",
      timeout: 2000,
      textColor: "white",
      actions: [{ icon: "close", color: "white" }]
    }
  }
});
