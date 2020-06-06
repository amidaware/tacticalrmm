import * as All from "quasar";
import Vue from "vue";

const { 
  Quasar,
  Dialog,
  Loading,
  LoadingBar,
  Meta,
  Notify,
  ClosePopup } = All;

const components = Object.keys(All).reduce((object, key) => {
  const val = All[key];
  if (val && val.component && val.component.name != null) {
    object[key] = val;
  }
  return object;
}, {});

Vue.use(Quasar, { 
  components,
  plugins: [
    Dialog,
    Loading,
    LoadingBar,
    Meta,
    Notify
  ],
  directives: [
    ClosePopup
  ]
});
