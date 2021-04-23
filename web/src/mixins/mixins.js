import { Notify, date } from "quasar";
import axios from 'axios'

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

    isValidThreshold(warning, error, diskcheck = false) {
      if (warning === 0 && error === 0) {
        Notify.create(notifyErrorConfig("Warning Threshold or Error Threshold need to be set", 2000));
        return false
      }

      if (!diskcheck && warning > error && warning > 0 && error > 0) {
        Notify.create(notifyErrorConfig("Warning Threshold must be less than Error Threshold", 2000));
        return false
      }

      if (diskcheck && warning < error && warning > 0 && error > 0) {
        Notify.create(notifyErrorConfig("Warning Threshold must be more than Error Threshold", 2000));
        return false
      }

      return true;
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
      if (!timestamp) return ""

      let t = new Date(timestamp * 1000)
      return date.formatDate(t, 'MMM-D-YYYY - HH:mm')
    },
    dateStringToUnix(drfString) {
      if (!drfString) return 0;
      const d = date.extractDate(drfString, "MM DD YYYY HH:mm");
      return parseInt(date.formatDate(d, "X"));
    },
    formatDjangoDate(drfString) {
      if (!drfString) return "";
      const d = date.extractDate(drfString, "MM DD YYYY HH:mm");
      return date.formatDate(d, "MMM-DD-YYYY - HH:mm");
    },
    formatClientOptions(clients) {
      return clients.map(client => ({ label: client.name, value: client.id, sites: client.sites }))
    },
    formatSiteOptions(sites) {
      return sites.map(site => ({ label: site.name, value: site.id }));
    },
    capitalize(string) {
      return string[0].toUpperCase() + string.substring(1);
    },
    getCustomFields(model) {
      return axios.patch("/core/customfields/", { model: model })
        .catch(e => {
          this.notifyError("There was an issue getting Custom Fields");
        });
    },
    getAgentCount(data, type, id) {
      if (type === "client") {
        return data.find(i => id === i.id).agent_count
      } else {
        const sites = data.map(i => i.sites)
        for (let i of sites) {
          for (let k of i) {
            if (k.id === id) return k.agent_count;
          }
        }
        return 0;
      }
    },
    formatCustomFields(fields, values) {
      let tempArray = [];

      for (let field of fields) {
        if (values[field.name] !== null || values[field.name] !== undefined)
          if (field.type === "multiple") {
            tempArray.push({ multiple_value: values[field.name], field: field.id });
          } else if (field.type === "checkbox") {
            tempArray.push({ bool_value: values[field.name], field: field.id });
          } else {
            tempArray.push({ string_value: values[field.name], field: field.id });
          }
      }
      return tempArray
    },
    getScriptOptions(showCommunityScripts = false) {
      let options = [];
      axios.get("/scripts/scripts/").then(r => {
        let scripts;
        if (showCommunityScripts) {
          scripts = r.data;
        } else {
          scripts = r.data.filter(i => i.script_type !== "builtin");
        }

        let categories = [];
        let create_unassigned = false
        scripts.forEach(script => {
          if (!!script.category && !categories.includes(script.category)) {
            categories.push(script.category);
          } else {
            create_unassigned = true
          }
        });

        if (create_unassigned) categories.push("Unassigned")

        categories.forEach(cat => {
          options.push({ category: cat });
          let tmp = [];
          scripts.forEach(script => {
            if (script.category === cat) {
              tmp.push({ label: script.name, value: script.id, timeout: script.default_timeout, args: script.args });
            } else if (cat === "Unassigned" && !script.category) {
              tmp.push({ label: script.name, value: script.id, timeout: script.default_timeout, args: script.args });
            }
          })
          const sorted = tmp.sort((a, b) => a.label.localeCompare(b.label));
          options.push(...sorted);
        });
      });

      return options;
    }
  }
}
