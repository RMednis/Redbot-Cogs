import io
import json
import logging
from typing import Literal

import discord
from discord import app_commands, PartialEmoji
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

from reactionroles import config_parser

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

log = logging.getLogger("red.mednis-cogs.reactionroles")

class ReactionRoles(commands.Cog):
    """
    A reaction role and embed setup cog
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=92651437657460736,
            force_registration=True,
        )

        self.config.register_guild(
            embeds=[]
        )

    async def embed_autocomplete(self, interaction: discord.Interaction, name: str):
        embed_configs = await self.config.guild(interaction.guild).embeds()

        return [
            discord.app_commands.Choice(name=embed_configs["name"], value=embed_configs["name"])
            for embed_configs in embed_configs
            if name in embed_configs["name"]
        ]

    async def embed_emote_autocomplete(self, interaction: discord.Interaction, emote: str):
        embed_configs = await self.config.guild(interaction.guild).embeds()
        name = interaction.namespace.name
        for embed in embed_configs:
            if embed["name"] == name:
                if "reaction_roles" not in embed:
                    return [ discord.app_commands.Choice(name="No Reaction Roles", value="None") ]
                return [
                    discord.app_commands.Choice(name=role["emoji"], value=role["emoji"])
                    for role in embed["reaction_roles"]
                    if emote in role["emoji"]
                ]
        return [ discord.app_commands.Choice(name="No Embed", value="None") ]

    embed = app_commands.Group(name="embed", description="Embed and Reaction role management", guild_only=True)



    @embed.command(name="create", description="Create a new embed")
    async def embed_create(self, interaction: discord.Interaction, name: str, config: discord.Attachment = None,
                           channel: discord.TextChannel = None):
        embed_configs = await self.config.guild(interaction.guild).embeds()

        # Defer the responsem, this might take a while
        await interaction.response.defer()

        if await config_parser.embed_exists(embed_configs, name):
            return await interaction.followup.send(f"Embed `{name}` already exists."
                                                           f"\nYou should modify it or remove it using `/embed edit {name}` "
                                                           f"or `/embed remove {name}`", ephemeral=False)

        if config is None:
            # Setup the default config and return it to the user
            default_config = await config_parser.default_config()
            default_config["name"] = name

            if channel is not None:
                # Set the channel
                default_config["channel"] = channel.id
                # Send the message
                message = await channel.send(embed=await config_parser.create_embed(default_config))
                default_config["message"] = message.id

            # Add the config to the list
            embed_configs.append(default_config)
            await self.config.guild(interaction.guild).embeds.set(embed_configs)

            # Create a config file for the user to download
            config_file = io.BytesIO(json.dumps(default_config, indent=4).encode('UTF-8'))

            return await interaction.followup.send("Embed created, but there is no config provided. "
                                                           "\nDownload and edit this config file, "
                                                           f"then upload it via `/embed edit {name}`", ephemeral=True,
                                                           file=discord.File(config_file,
                                                                             filename=f"embed_{name}.json"))
        else:
            if "application/json" not in config.content_type:
                return await interaction.followup.send("Invalid attachment type", ephemeral=False)

            try:
                # Read the attachment
                data = await config.read()

                # Load and parse the settings
                settings = json.loads(data)
                await config_parser.parse_config(settings)

                # Create the embed
                channel = interaction.guild.get_channel(settings["channel"])

                if channel is None:
                    return await interaction.followup.send("Invalid channel", ephemeral=False)

                message = await channel.send(embed=await config_parser.create_embed(settings))
                settings["message"] = message.id
                await self.config.guild(interaction.guild).embeds.set(embed_configs)
                # Add the config to the list
                embed_configs.append(settings)
                await self.config.guild(interaction.guild).embeds.set(embed_configs)

                return await interaction.followup.send(f"Embed `{name}` has been created", ephemeral=False)
            except json.JSONDecodeError:
                return await interaction.followup.send("Error loading config: `Invalid JSON`", ephemeral=False)
            except config_parser.ConfigError as e:
                return await interaction.followup.send(f"Error loading config: `{str(e)}`", ephemeral=False)

    @app_commands.autocomplete(name=embed_autocomplete)
    @embed.command(name="edit", description="Edit an existing embed")
    async def embed_edit(self, interaction: discord.Interaction, name: str, config: discord.Attachment = None):
        embed_configs = await self.config.guild(interaction.guild).embeds()

        await interaction.followup.defer()

        if not await config_parser.embed_exists(embed_configs, name):
            return await interaction.followup.send(f"Embed `{name}` does not exist."
                                                           f"\nYou should create it using `/embed create {name}`",
                                                           ephemeral=True)

        if config is None:
            # Get the config
            config = await config_parser.find_embed(embed_configs, name)

            # Create a config file for the user to download
            config_file = io.BytesIO(json.dumps(config, indent=4).encode('UTF-8'))

            return await interaction.followup.send("Download and edit this config file, "
                                                           f"then upload it via `/embed edit {name}`", ephemeral=True,
                                                           file=discord.File(config_file,
                                                                             filename=f"embed_{name}.json"))

        if "application/json" not in config.content_type:
            return await interaction.followup.send("Invalid attachment type", ephemeral=False)

        try:
            # Read the attachment
            data = await config.read()

            # Load and parse the settings
            settings = json.loads(data)
            await config_parser.parse_config(settings)

        except json.JSONDecodeError:
            return await interaction.followup.send("Error loading config: `Invalid JSON`", ephemeral=False)
        except config_parser.ConfigError as e:
            return await interaction.followup.send(f"Error loading config: `{str(e)}`", ephemeral=False)

        # Find the embed, edit it
        channel = interaction.guild.get_channel(settings["channel"])
        message = await channel.fetch_message(settings["message"])
        await message.edit(embed=await config_parser.create_embed(settings))

        # Update the config
        for i, embed in enumerate(embed_configs):
            if embed["name"] == name:
                embed_configs[i] = settings
                break

        await self.config.guild(interaction.guild).embeds.set(embed_configs)

        return await interaction.followup.send(f"Embed `{name}` has been updated", ephemeral=False)

    @app_commands.autocomplete(name=embed_autocomplete)
    @embed.command(name="remove", description="Remove a existing embed")
    async def embed_remove(self, interaction: discord.Interaction, name: str, delete_messages: bool = False):
        embed_configs = await self.config.guild(interaction.guild).embeds()

        await interaction.response.defer()

        if not await config_parser.embed_exists(embed_configs, name):
            return await interaction.followup.send(f"Embed `{name}` does not exist."
                                                           f"\nYou should create it using `/embed create {name}`",
                                                           ephemeral=True)

        try:
            # Find the embed
            embed_config = await config_parser.find_embed(embed_configs, name)

            # Delete the message if requested
            if delete_messages:
                channel = interaction.guild.get_channel(embed_config["channel"])
                if channel is not None:
                    message = await channel.fetch_message(embed_config["message"])
                    if message is not None:
                        await message.delete()

            # Remove the embed from the list
            embed_configs.remove(embed_config)
            await self.config.guild(interaction.guild).embeds.set(embed_configs)

        except config_parser.ConfigError as e:
            return await interaction.followup.send(f"Error removing embed: `{str(e)}`", ephemeral=False)

        except discord.HTTPException as e:
            return await interaction.followup.send(f"Error removing embed: `{str(e)}`", ephemeral=False)


        await self.config.guild(interaction.guild).embeds.set(embed_configs)
        return await interaction.followup.send(f"Embed `{name}` has been removed", ephemeral=False)

    @app_commands.autocomplete(name=embed_autocomplete)
    @embed.command(name="add_reaction", description="Add a reaction role to an existing embed")
    async def embed_add_reaction(self, interaction: discord.Interaction, name: str, emoji: str, role: discord.Role, unique: bool = False):

        await interaction.response.defer()
        embed_configs = await self.config.guild(interaction.guild).embeds()

        if not await config_parser.embed_exists(embed_configs, name):
            return await interaction.followup.send(f"Embed `{name}` does not exist."
                                                           f"\nYou should create it using `/embed create {name}`",
                                                           ephemeral=False)

        partial_emoji = PartialEmoji.from_str(emoji)

        # Find the embed
        embed_config = await config_parser.find_embed(embed_configs, name)

        # Check if the embed has reaction roles
        # If not, create an empty list
        if not await config_parser.has_reaction_roles(embed_config):
            embed_config["reaction_roles"] = []


        # Check if the emoji already has a role
        reaction_roles = await config_parser.get_reaction_roles(embed_config, emoji)
        if len(reaction_roles) > 0:
            return await interaction.followup.send(f"Reaction role for `{emoji}` already exists."
                                                   f"Remove it with `/embed remove_reaction {name} {emoji}`",
                                                   ephemeral=False)

        # Role Permission Checks
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.followup.send("You do not have permission to manage roles", ephemeral=False)

        if not interaction.guild.me.guild_permissions.manage_roles:
            return await interaction.followup.send("I do not have permission to manage roles", ephemeral=False)

        if role >= interaction.guild.me.top_role:
            return await interaction.followup.send(f"Role {role.mention} is higher than the bot's top role"
                                                   f" {interaction.guild.me.top_role.mention}", ephemeral=False)

        if role >= interaction.user.top_role:
            return await interaction.followup.send(f"Role {role.mention} is higher than your top role"
                                                   f" {interaction.user.top_role.mention}", ephemeral=False)

        # Add the reaction to the message
        try:
            channel = interaction.guild.get_channel(embed_config["channel"])
            if channel is not None:
                message = await channel.fetch_message(embed_config["message"])
                if message is not None:
                    reaction_roles = embed_config["reaction_roles"]

                    # Add the reaction, if it fails, it's likely an invalid emoji
                    await message.add_reaction(emoji)

                    # Add the reaction role
                    reaction_roles.append(await config_parser.create_reaction_role(str(partial_emoji), role.id, unique))

                    # Update the config
                    for i, embed in enumerate(embed_configs):
                        if embed["name"] == name:
                            embed_configs[i]["reaction_roles"] = reaction_roles
                            break
                    await self.config.guild(interaction.guild).embeds.set(embed_configs)

                    return await interaction.followup.send(f"Reaction role added for `{emoji}` to {role.mention}",
                                                           ephemeral=False)
        except discord.HTTPException as e:
            if e.code == 10014:
                return await interaction.followup.send(f"Invalid emoji `{emoji}` - I can only add Emoji from this server.", ephemeral=False)
            return await interaction.followup.send(f"Error adding reaction: `{str(e)}`", ephemeral=False)

    @app_commands.autocomplete(name=embed_autocomplete, emoji=embed_emote_autocomplete)
    @embed.command(name="remove_reaction", description="Remove a reaction role from an existing embed")
    async def embed_remove_reaction(self, interaction: discord.Interaction, name: str, emoji: str):
        await interaction.response.defer()
        embed_configs = await self.config.guild(interaction.guild).embeds()

        if not await config_parser.embed_exists(embed_configs, name):
            return await interaction.followup.send(f"Embed `{name}` does not exist."
                                                           f"\nYou should create it using `/embed create {name}`",
                                                           ephemeral=False)

        # Find the embed
        embed_config = await config_parser.find_embed(embed_configs, name)

        # Check if the embed has reaction roles
        if not await config_parser.has_reaction_roles(embed_config):
            return await interaction.followup.send(f"Embed `{name}` does not have any reaction roles", ephemeral=False)

        # Check if the emoji already has a role
        reaction_roles_with_emoji = await config_parser.get_reaction_roles(embed_config, emoji)
        if len(reaction_roles_with_emoji) == 0:
            return await interaction.followup.send(f"Reaction role for `{emoji}` does not exist.", ephemeral=False)

        # Get the reaction roles
        reaction_roles = embed_config["reaction_roles"]
        reaction_roles = [role for role in reaction_roles if role["emoji"] != emoji]

        # Remove the reaction from the message
        channel = interaction.guild.get_channel(embed_config["channel"])
        if channel is not None:
            message = await channel.fetch_message(embed_config["message"])
            if message is not None:
                await message.clear_reaction(emoji)

        # Update the config
        for i, embed in enumerate(embed_configs):
            if embed["name"] == name:
                embed_configs[i]["reaction_roles"] = reaction_roles
                break
        await self.config.guild(interaction.guild).embeds.set(embed_configs)

        return await interaction.followup.send(f"Reaction role removed for `{emoji}`", ephemeral=False)


    @app_commands.autocomplete(embed=embed_autocomplete)
    @embed.command(name="reaction_list", description="List reaction roles")
    async def embed_reaction_list(self, interaction: discord.Interaction, embed: str):
        embed_configs = await self.config.guild(interaction.guild).embeds()

        await interaction.response.defer()

        if not await config_parser.embed_exists(embed_configs, embed):
            return await interaction.followup.send(f"Embed `{embed}` does not exist."
                                                           f"\nYou should create it using `/embed create {embed}`",
                                                           ephemeral=False)

        # Find the embed
        embed_config = await config_parser.find_embed(embed_configs, embed)

        # Check if the embed has reaction roles
        if not await config_parser.has_reaction_roles(embed_config):
            return await interaction.followup.send(f"Embed `{embed}` does not have any reaction roles", ephemeral=False)

        # Get the reaction roles
        reaction_roles = embed_config["reaction_roles"]
        if len(reaction_roles) == 0:
            return await interaction.followup.send(f"Embed `{embed}` does not have any reaction roles.", ephemeral=False)
        else:
            # Create the message
            message = f"Reaction roles for `{embed}`:"
            for role in reaction_roles:
                message += f"\n- {role['emoji']} - <@&{role['role']}>"
                if role["unique"]:
                    message += " _(Unique)_"
            return await interaction.followup.send(message, ephemeral=False)


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        embed_configs = await self.config.guild_from_id(payload.guild_id).embeds()
        config = await config_parser.find_embed_by_id(embed_configs, payload.message_id)

        for reaction_role in config["reaction_roles"]:
            if reaction_role["emoji"] == str(payload.emoji):
                guild = self.bot.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)
                added_role = guild.get_role(reaction_role["role"])

                # Remove all other roles if unique is set on the added role
                if reaction_role["unique"]:
                    # Remove the reaction
                    channel = guild.get_channel(config["channel"])
                    message = await channel.fetch_message(config["message"])

                    for role in config["reaction_roles"]:
                        if role["emoji"] != str(payload.emoji):
                            await message.remove_reaction(role["emoji"], member)

                await member.add_roles(added_role, reason=f"Reaction Role in embed {config['name']}")
                return

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        embed_configs = await self.config.guild_from_id(payload.guild_id).embeds()
        config = await config_parser.find_embed_by_id(embed_configs, payload.message_id)

        for role in config["reaction_roles"]:
            if role["emoji"] == str(payload.emoji):
                guild = self.bot.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)

                removed_role = guild.get_role(role["role"])
                await member.remove_roles(removed_role, reason=f"Reaction Role in embed {config['name']}")
                return
    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)
