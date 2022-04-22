import { Notify, date } from "quasar";
import axios from 'axios'

import { formatAgentOptions } from "@/utils/format"

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

export default {
  methods: {
    bootTime(unixtime) {
      return getTimeLapse(unixtime);
    },
    alertTime(unixtime) {
      return getTimeLapse(unixtime);

    },
    notifySuccess(msg, timeout = 2000) {
      Notify.create({
        type: "positive",
        message: msg,
        timeout: timeout
      });
    },
    notifyError(msg, timeout = 2000) {
      Notify.create({
        type: "negative",
        message: msg,
        timeout: timeout
      });
    },
    notifyWarning(msg, timeout = 2000) {
      Notify.create({
        type: "warning",
        message: msg,
        timeout: timeout
      });
    },
    notifyInfo(msg, timeout = 2000) {
      Notify.create({
        type: "info",
        message: msg,
        timeout: timeout
      });
    },

    isValidThreshold(warning, error, diskcheck = false) {
      if (warning === 0 && error === 0) {
        Notify.create({ type: "negative", timeout: 2000, message: "Warning Threshold or Error Threshold need to be set" });
        return false;
      }

      if (!diskcheck && warning > error && warning > 0 && error > 0) {
        Notify.create({ type: "negative", timeout: 2000, message: "Warning Threshold must be less than Error Threshold" });
        return false;
      }

      if (diskcheck && warning < error && warning > 0 && error > 0) {
        Notify.create({ type: "negative", timeout: 2000, message: "Warning Threshold must be more than Error Threshold" });
        return false;
      }

      return true;
    },
    isValidEmail(val) {
      const email = /^(?=[a-zA-Z0-9@._%+-]{6,254}$)[a-zA-Z0-9._%+-]{1,64}@(?:[a-zA-Z0-9-]{1,63}\.){1,8}[a-zA-Z]{2,63}$/;
      return email.test(val);
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
    async getScriptOptions(showCommunityScripts = false) {
      let options = [];
      const { data } = await axios.get("/scripts/")
      let scripts;
      if (showCommunityScripts) {
        scripts = data;
      } else {
        scripts = data.filter(i => i.script_type !== "builtin");
      }

      let categories = [];
      let create_unassigned = false
      scripts.forEach(script => {
        if (!!script.category && !categories.includes(script.category)) {
          categories.push(script.category);
        } else if (!script.category) {
          create_unassigned = true
        }
      });

      if (create_unassigned) categories.push("Unassigned")

      categories.sort().forEach(cat => {
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

      return options;
    },
    async getAgentOptions(value_field = "agent_id") {

      const { data } = await axios.get("/agents/?detail=false")

      return formatAgentOptions(data, false, value_field)
    },
    getNextAgentUpdateTime() {
      const d = new Date();
      let ret;
      if (d.getMinutes() <= 35) {
        ret = d.setMinutes(35);
      } else {
        ret = date.addToDate(d, { hours: 1 });
        ret.setMinutes(35);
      }
      const a = date.formatDate(ret, "MMM D, YYYY");
      const b = date.formatDate(ret, "h:mm A");
      return `${a} at ${b}`;
    },
    truncateText(txt) {
      if (txt)
        return txt.length >= 60 ? txt.substring(0, 60) + "..." : txt;
      else return ""
    },
  }
}
