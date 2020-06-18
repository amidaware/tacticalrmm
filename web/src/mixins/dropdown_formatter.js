export default {
  methods: {
    formatClients(clients) {
      return clients.map(client => ({
          label: client.client,
          value: client.id
        })
      );
    },
    formatSites(sites) {
      return sites.map(site => ({
          label: site.site,
          value: site.id,
          client: site.client_name
        })
      );
    }
  }
};
