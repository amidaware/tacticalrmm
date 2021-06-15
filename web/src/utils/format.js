
export function formatAgentOptions(data) {
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