 Pastures Integration
---

A custom-made redbot cog for connecting the greener pastures minecraft server and discord servers.

This cog provides 2 functions:
- The ability to see currently online players via a live-updating message embed
- The ability to do _one-click_ whitelisting of users by adding a 👍 emote to a message containing a username.

_This cog isn't really meant for public consumption, all the branding is currently baked into the main embed function, with no direct way of editing it!_

## Screenshot Examples

- Persistent Server Status Embed  
![Embed Example](example.png)


## Commands

- `pastures` - The main cog config command!
    - `config` - Used for setting the main RCON credentials i.e. `<Server IP> <Rcon Password>`
    - `players` - Returns a non-updating, one time embed with the server/player status
    - `embed` - Controls the live-updating persistent embed
      - `add` - Post an embed to a channel! (Add the channel name with #<channel>)
      - `remove` - Removes the embed and stops live updating

## Setup
Add the repository: ``[!]repo add Mednis-Cogs https://github.com/RMednis/Redbot-Cogs``

Install the dependencies: 
``[!]pipinstall mojang``, ``[!]pipinstall aio-mc-rcon``

Install the cog: ``[!]cog install Mednis-Cogs pastures_integration``

Load the cog: ``[!]load pastures_integration``

