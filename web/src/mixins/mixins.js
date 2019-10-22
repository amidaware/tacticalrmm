import { Notify } from "quasar";

export default {
  methods: {
    bootTime(unixtime) {
      var previous = unixtime * 1000;
      var current = new Date();
      var msPerMinute = 60 * 1000;
      var msPerHour = msPerMinute * 60;
      var msPerDay = msPerHour * 24;
      var msPerMonth = msPerDay * 30;
      var msPerYear = msPerDay * 365;
      var elapsed = current - previous;
      if (elapsed < msPerMinute) {
        return Math.round(elapsed / 1000) + " seconds ago";
      } else if (elapsed < msPerHour) {
        return Math.round(elapsed / msPerMinute) + " minutes ago";
      } else if (elapsed < msPerDay) {
        return Math.round(elapsed / msPerHour) + " hours ago";
      } else if (elapsed < msPerMonth) {
        return Math.round(elapsed / msPerDay) + " days ago";
      } else if (elapsed < msPerYear) {
        return Math.round(elapsed / msPerMonth) + " months ago";
      } else {
        return Math.round(elapsed / msPerYear) + " years ago";
      }
    },
    notifySuccess(msg) {
      Notify.create({
        color: "green",
        icon: "fas fa-check-circle",
        message: msg
      });
    },
    notifyError(msg) {
      Notify.create({
        color: "red",
        icon: "fas fa-times-circle",
        message: msg
      });
    }
  }
};
