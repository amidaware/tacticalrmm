
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