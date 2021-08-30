# Database Maintenance

Tactical RMM ships with data retention defaults that will work fine for most environments. There are situations, depending on the number of agents and checks configured, that these defaults need to be tweaked to improve performance.

## Adjusting Data Retention

In the dashboard, go to **Settings > Global Settings > Retention**

The options are:

- **Check History** - Will delete check history older than the days specified (default is 30 days).
- **Resolved Alerts** - Will delete alerts that have been resolved older than the days specified (default is disabled).
- **Agent History** - Will delete agent command/script history older than the days specified (default is 60 days).
- **Debug Logs** - Will delete agent debug logs older than the days specified (default is 30 days)
- **Audit Logs** Will delete Tactical RMM audit logs older than the days specified (default is disabled)

To disable database pruning on a table, set the days to 0.
