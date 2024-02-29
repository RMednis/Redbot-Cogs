import logging
import re
from datetime import datetime, timedelta
from typing import Literal

import discord
from discord import app_commands
from discord.ext import tasks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]
log = logging.getLogger("red.mednis-cogs.vxer")


async def get_link(text, url) -> str:
    url_re = re.compile(r"https?://(?:\w+\.)?" + re.escape(url) + r"\S+")
    found_url = url_re.search(text)

    if found_url:
        return found_url.group(0)
    else:
        raise ValueError("No match found")


async def change_link(message: discord.Message, og_site, replacement_site: str) -> None:
    link = await get_link(message.content, og_site)
    link = link.replace(og_site, replacement_site)

    if link == f"https://{replacement_site}/":
        raise ValueError("No match found")

    await message.reply(link, mention_author=False)


class VxEr(commands.Cog):
    """
    Converts TikTok and Twitter links to their embeddable versions
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=92651437657460736,
            force_registration=True,
        )

        default_guild = {
            "tiktok": True,
            "twitter": True,
            "tiktok_replacement": "vxtiktok.com",
            "twitter_replacement": "vxtwitter.com",
            "messages": []
        }

        self.config.register_guild(**default_guild)
        self.cleanup_messages.start()

    async def cog_unload(self) -> None:
        self.cleanup_messages.cancel()
        # Clear the messages list for all guilds
        log.info("Clearing messages list for all guilds!")
        for guild in self.bot.guilds:
            await self.config.guild(guild).messages.set([])

    def __unload__(self) -> None:
        self.cleanup_messages.cancel()

    async def add_message_to_list(self, message: discord.Message) -> None:
        async with self.config.guild(message.guild).messages() as messages:
            deletion_time = datetime.utcnow() + timedelta(minutes=1)
            messages.append((message.id, message.channel.id, deletion_time.timestamp()))

    async def remove_message_from_list(self, message: discord.Message) -> None:
        messages = await self.config.guild(message.guild).messages()
        messages = [t for t in messages if t[0] != message.id]
        await self.config.guild(message.guild).messages.set(messages)

    @tasks.loop(minutes=1)
    async def cleanup_messages(self) -> None:
        for guild in self.bot.guilds:
            async with self.config.guild(guild).messages() as messages:
                for message in messages:
                    if datetime.fromtimestamp(message[2]) < datetime.utcnow():
                        messages.remove(message)
                        try:
                            message = await guild.get_channel(message[1]).fetch_message(message[0])
                            await message.remove_reaction("🎵", self.bot.user)
                            await message.remove_reaction("🐦", self.bot.user)
                        except discord.errors.NotFound:
                            pass

    vxer_group = app_commands.Group(name="vxer", description="Setup VxEr settings", guild_only=True)

    @vxer_group.command(name="tiktok", description="Enable or disable TikTok link conversion")
    @app_commands.describe(enable="Enable or disable TikTok link conversion")
    @app_commands.describe(vxtiktok="The replacement for the TikTok link")
    @commands.guild_only()
    async def vxer_tiktok(self, interaction: discord.Interaction, enable: bool, vxtiktok: str = None) -> None:

        await self.config.guild(interaction.guild).tiktok.set(enable)

        if vxtiktok is not None:
            await self.config.guild(interaction.guild).tiktok_replacement.set(vxtiktok)
        else:
            vxtiktok = await self.config.guild(interaction.guild).tiktok_replacement()

        await interaction.response.send_message(f"TikTok link conversion `{'enabled' if enable else 'disabled'}`"
                                                f" with replacement `{vxtiktok}`")

    @vxer_group.command(name="twitter", description="Enable or disable Twitter link conversion")
    @app_commands.describe(enable="Enable or disable Twitter link conversion")
    @app_commands.describe(vxtwitter="The replacement for the Twitter link")
    @commands.guild_only()
    async def vxer_twitter(self, interaction: discord.Interaction, enable: bool, vxtwitter: str = None) -> None:

        await self.config.guild(interaction.guild).twitter.set(enable)

        if vxtwitter is not None:
            await self.config.guild(interaction.guild).twitter_replacement.set(vxtwitter)
        else:
            vxtwitter = await self.config.guild(interaction.guild).twitter_replacement()

        await interaction.response.send_message(f"Twitter link conversion `{'enabled' if enable else 'disabled'}`"
                                                f" with replacement `{vxtwitter}`")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:

        # Check if the message is from a guild
        if not message.guild:
            return

        # Check if the message is from a bot
        if message.author.bot:
            return

        # Check if the message is already a vx-ed link
        # "vxt" works for both vxTikTok and vxTwitter
        if "vxt" in message.content:
            return

        # Check if TikTok link conversion is enabled
        if await self.config.guild(message.guild).tiktok():

            # Check if the message is a TikTok link
            if "tiktok.com/" in message.content:
                await self.add_message_to_list(message)
                await message.add_reaction("🎵")
                return

        # Check if Twitter link conversion is enabled
        if await self.config.guild(message.guild).twitter():

            # Check if the message is a Twitter link
            if "twitter.com/" in message.content:
                await self.add_message_to_list(message)
                await message.add_reaction("🐦")
                return

            # Check if the message is a X.com link
            if "x.com/" in message.content:
                await self.add_message_to_list(message)
                await message.add_reaction("🐦")
                return

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User) -> None:

        # Bail if the reaction is from a bot or if the message is from a DM
        # Bailing here is faster than bailing later
        if user.bot is True or reaction.message.guild is None:
            return

        # Bail if the message is in the list of messages
        messages = await self.config.guild(reaction.message.guild).messages()
        if not any(mes[0] == reaction.message.id for mes in messages):
            return

        # The bots user ID
        user_id = self.bot.user.id
        is_in_list = False

        # Check if the bot has reacted to the message
        for reaction in reaction.message.reactions:
            async for user in reaction.users():
                if user.id == user_id:
                    is_in_list = True
                    break

        # Bail If the bot has not reacted to the message
        if not is_in_list:
            return

        # Remove the message from the list
        await self.remove_message_from_list(reaction.message)

        # If the reaction emoji is not a TikTok link, add it
        if reaction.emoji == "🎵":
            try:
                # Try to remove the reaction
                await reaction.message.remove_reaction("🎵", self.bot.user)
            except discord.errors.Forbidden:
                # We just give up
                return

            alternative = await self.config.guild(reaction.message.guild).tiktok_replacement()

            try:
                await change_link(reaction.message, "tiktok.com", alternative)
                return
            except ValueError:
                # We want this to be silent, so we just give up
                log.error("Tried to change a TikTok link, but no REGEX match was found.\n"
                          f"GUILD: {reaction.message.guild.id} MESSAGE: {reaction.message.id}")
                return

        # Check if the reaction is from a Twitter link
        if reaction.emoji == "🐦":
            try:
                # Try to remove the reaction
                await reaction.message.remove_reaction("🐦", self.bot.user)
            except discord.errors.Forbidden:
                # We just give up
                return

            alternative = await self.config.guild(reaction.message.guild).twitter_replacement()
            try:
                # It might be a Twitter link
                await change_link(reaction.message, "twitter.com", alternative)
                return
            except ValueError:
                try:
                    # It might be a X.com link
                    await change_link(reaction.message, "x.com", alternative)
                    return
                except ValueError:
                    # It wasn't an X.com link either, so we just give up
                    log.error("Tried to change a X/Twitter link, but no REGEX match was found.\n"
                              f"GUILD: {reaction.message.guild.id} MESSAGE: {reaction.message.id}")
                    return

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # We don't store any user data
        # No action is needed
        return
