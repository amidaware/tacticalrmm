
// dropdown options formatting

function _formatOptions(data, { label, value = "id", flat = false, allowDuplicates = true }) {
  if (!flat)
    // returns array of options in object format [{label: label, value: 1}]
    return data.map(i => ({ label: i[label], value: i[value] }));
  else
    // returns options as an array of strings ["label", "label1"]
    if (!allowDuplicates)
      return data.map(i => i[label]);
    else {
      const options = []
      data.forEach(i => {
        if (!options.includes(i[label]))
          options.push(i[label])
      });
      return options
    }
}

export function formatScriptOptions(data, flat = false) {
  if (flat) {
    // returns just script names in array
    return _formatOptions(data, { label: "name", value: "pk", flat: true, allowDuplicates: false })
  } else {

    let options = [];
    let categories = [];
    let create_unassigned = false
    data.forEach(script => {
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
      data.forEach(script => {
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
  }
}

export function formatAgentOptions(data, flat = false) {

  if (flat) {
    // returns just agent hostnames in array
    return _formatOptions(data, { label: "hostname", value: "pk", flat: true, allowDuplicates: false })
  } else {
    // returns options with categories in object format
    let options = []
    const agents = data.map(agent => ({
      label: agent.hostname,
      value: agent.pk,
      cat: `${agent.client} > ${agent.site}`,
    }));

    let categories = [];
    agents.forEach(option => {
      if (!categories.includes(option.cat)) {
        categories.push(option.cat);
      }
    });

    categories.sort().forEach(cat => {
      options.push({ category: cat });
      let tmp = []
      agents.forEach(agent => {
        if (agent.cat === cat) {
          tmp.push(agent);
        }
      });

      const sorted = tmp.sort((a, b) => a.label.localeCompare(b.label));
      options.push(...sorted);
    });

    return options
  }
}

export function formatCustomFieldOptions(data, flat = false) {
  if (flat) {
    return _formatOptions(data, { label: "name", flat: true })
  }
  else {
    const categories = ["Client", "Site", "Agent"]
    const options = []

    categories.forEach(cat => {
      options.push({ category: cat });
      const tmp = [];
      data.forEach(custom_field => {
        if (custom_field.model === cat.toLowerCase()) {
          tmp.push({ label: custom_field.name, value: custom_field.id })
        }
      });

      const sorted = tmp.sort((a, b) => a.label.localeCompare(b.label));
      options.push(...sorted);
    })

    return options
  }
}

export function formatClientOptions(data, flat = false) {
  return _formatOptions(data, { label: "name", flat: flat })
}

export function formatSiteOptions(data, flat = false) {
  const options = []

  data.forEach(client => {
    options.push({ category: client.name });
    options.push(..._formatOptions(client.sites, { label: "name", flat: flat }))
  });

  return options
}

export function formatUserOptions(data, flat = false) {
  return _formatOptions(data, { label: "username", flat: flat })
}


// date formatting

function _appendLeadingZeroes(n) {
  if (n <= 9) {
    return "0" + n;
  }
  return n
}

export function formatDate(date, includeSeconds = false) {
  if (!date) return
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  let dt = new Date(date)
  let formatted = months[dt.getMonth()] + "-" + _appendLeadingZeroes(dt.getDate()) + "-" + _appendLeadingZeroes(dt.getFullYear()) + " - " + _appendLeadingZeroes(dt.getHours()) + ":" + _appendLeadingZeroes(dt.getMinutes())

  return includeSeconds ? formatted + ":" + _appendLeadingZeroes(dt.getSeconds()) : formatted
}


// string formatting

export function capitalize(string) {
  return string[0].toUpperCase() + string.substring(1);
}

export function formatTableColumnText(text) {

  let string = ""
  // split at underscore if exists
  const words = text.split("_")
  words.forEach(word => string = string + " " + capitalize(word))

  return string.trim()
}

export function truncateText(txt, chars) {
  if (!txt) return

  return txt.length >= chars ? txt.substring(0, chars) + "..." : txt;
}