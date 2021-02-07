import { Notify, date } from "quasar";

export function notifySuccessConfig(msg, timeout = 2000) {
  return {
    type: "positive",
    message: msg,
    timeout: timeout
  }
};

export function notifyErrorConfig(msg, timeout = 2000) {
  return {
    type: "negative",
    message: msg,
    timeout: timeout
  }
};

export function notifyWarningConfig(msg, timeout = 2000) {
  return {
    type: "warning",
    message: msg,
    timeout: timeout
  }
};

export function notifyInfoConfig(msg, timeout = 2000) {
  return {
    type: "info",
    message: msg,
    timeout: timeout
  }
};

function getTimeLapse(unixtime) {
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
}

function appendLeadingZeroes(n) {
  if (n <= 9) {
    return "0" + n;
  }
  return n
}

export default {
  methods: {
    bootTime(unixtime) {
      return getTimeLapse(unixtime);
    },
    alertTime(unixtime) {
      return getTimeLapse(unixtime);

    },
    notifySuccess(msg, timeout = 2000) {
      Notify.create(notifySuccessConfig(msg, timeout));
    },
    notifyError(msg, timeout = 2000) {
      Notify.create(notifyErrorConfig(msg, timeout));
    },
    notifyWarning(msg, timeout = 2000) {
      Notify.create(notifyWarningConfig(msg, timeout));
    },
    notifyInfo(msg, timeout = 2000) {
      Notify.create(notifyInfoConfig(msg, timeout));
    },
    isValidEmail(val) {
      const email = /^(?=[a-zA-Z0-9@._%+-]{6,254}$)[a-zA-Z0-9._%+-]{1,64}@(?:[a-zA-Z0-9-]{1,63}\.){1,8}[a-zA-Z]{2,63}$/;
      return email.test(val);
    },
    formatDate(date, includeSeconds = false) {
      if (!date) return
      const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      let dt = new Date(date)
      let formatted = months[dt.getMonth()] + "-" + appendLeadingZeroes(dt.getDate()) + "-" + appendLeadingZeroes(dt.getFullYear()) + " - " + appendLeadingZeroes(dt.getHours()) + ":" + appendLeadingZeroes(dt.getMinutes())

      return includeSeconds ? formatted + ":" + appendLeadingZeroes(dt.getSeconds()) : formatted
    },
    unixToString(timestamp) {
      let t = new Date(timestamp * 1000)
      return date.formatDate(t, 'MMM-D-YYYY - HH:mm')
    },
    formatClientOptions(clients) {
      return clients.map(client => ({ label: client.name, value: client.id, sites: client.sites }))
    },
    formatSiteOptions(sites) {
      return sites.map(site => ({ label: site.name, value: site.id }))
    },
    capitalize(string) {
      return string[0].toUpperCase() + string.substring(1)
    }
  }
};
