export default {
  methods: {
    formatClients (clients) {
      return clients.map(client => {
        return {
          label: client.client,
          value: client.id
        };
      });
    },
    formatSites (sites) {
      return sites.map(site => {
        return {
          label: `${site.client_name}\\${site.site}`,
          value: site.id
        };
      });
    },
    formatAgents (agents) {
      return agents.map(agent => {
        return {
          label: `${agent.client}\\${agent.site}\\${agent.hostname}`,
          value: agent.pk
        };
      });
    },
  }
};
