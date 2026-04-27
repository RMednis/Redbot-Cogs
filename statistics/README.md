# Setting up the Statistics Server Infrastructure

1. Install and setup docker (and docker-compose if you are using an older version of docker)
2. Clone the repository
3. Create a `.env` file in the root of the repository and add the following environment variables
```bash
DATABASE_USER=<Your database user name>
DATABASE_PASSWORD=<Your database password>
DATABASE_ORG=<Your database org>
```
4. Run the following command to start the server
```bash
docker compose up
```
5. By default, the influxdb server will be running on port `8086` and the grafana server will be running on port `3000`
6. Connect to the grafana server and add the influxdb server as a data source, more info here: 
https://docs.influxdata.com/influxdb/v2/tools/grafana/?t=InfluxQL

# Setting up the Statistics Cog
All setup commands can only be run by the bot owner and are DM only.

> [!IMPORTANT]  
> This cog does not use slash commands. All commands are DM only.


1. Install the cog using the command: ``[!]cog install Mednis-Cogs statistics``
2. Load the cog using the command: ``[!]load statistics``
3. Configure the cog using the command: ``[!]set_statistics_db <address> <bucket> <org> <token>``

## Optional toggles
The cog has several optional logging methods that can be toggled on and off. These include:
- Voice Channel Statistics (`log_vc_stats`)
- Message Statistics (`log_message_stats`)
- Member Status and General Statistics (`log_member_stats`)
- Bot Statistics (`log_bot_stats`)
- External Statistics from other cogs (if they have been configured/support sending them) (`log_external_stats`)

By default the bot and external statistics are enabled, everything else can be optionally enabled.

To change and toggle these settings, use the following command:
`[!]set_logging_level <log_vc_stats> <log_message_stats> <log_member_stats> <log_bot_stats> <log_external_stats>`

Example:
``[!]set_logging_level true false true false true``

This will log voice channel statistics, member status and general statistics, and external statistics, but will not log message statistics or bot statistics.