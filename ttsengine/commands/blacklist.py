import discord
from redbot.core import app_commands
from redbot.core.bot import Red

from ttsengine.commands.base import TTSBase

class BlacklistCommands(TTSBase):
    tts_blacklist = app_commands.Group(name="tts_blacklist", description="TTS Blacklist", guild_only=True)

    async def blacklist_add(self, interaction: discord.Interaction, user: discord.Member):
        blacklist = await self.config.guild(interaction.guild).blacklisted_users()
        if user.id not in blacklist:
            blacklist.append(user.id)
            await self.config.guild(interaction.guild).blacklisted_users.set(blacklist)
            await interaction.response.send_message(f"Added user {user.mention} to blacklist!",
                                                    allowed_mentions=discord.AllowedMentions(users=False))
        else:
            await interaction.response.send_message(f"{user.mention} is already blacklisted!",
                                                    allowed_mentions=discord.AllowedMentions(users=False))

    @tts_blacklist.command(name="add", description="Prevent a user from using the TTS")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def blacklist_add_cmd(self, interaction: discord.Interaction, user: discord.Member):
        await self.blacklist_add(interaction, user)

    @tts_blacklist.command(name="remove", description="Allow a  user to use TTS")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def blacklist_remove_cmd(self, interaction: discord.Interaction[Red], user: discord.Member):
        await self.blacklist_remove(interaction, user)

    async def blacklist_remove(self, interaction: discord.Interaction, user: discord.Member):
        blacklist = await self.config.guild(interaction.guild).blacklisted_users()
        if user.id in blacklist:
            blacklist.remove(user.id)
            await self.config.guild(interaction.guild).blacklisted_users.set(blacklist)
            await interaction.response.send_message(f"Removed {user.mention} from blacklist!",
                                                    allowed_mentions=discord.AllowedMentions(users=False))
        else:
            await interaction.response.send_message(f"{user.mention} is not in the blacklist!",
                                                    allowed_mentions=discord.AllowedMentions(users=False))

    @tts_blacklist.command(name="list", description="List all blacklisted users")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def blacklist_list(self, interaction: discord.Interaction):
        blacklist = await self.config.guild(interaction.guild).blacklisted_users()

        user_list = ""
        stale_ids = []

        for user_id in blacklist:
            member = interaction.guild.get_member(user_id)
            if member:
                user_list += f"{member.display_name}\n"
            else:
                stale_ids.append(user_id)

        if stale_ids:
            cleaned = [uid for uid in blacklist if uid not in stale_ids]
            await self.config.guild(interaction.guild).blacklisted_users.set(cleaned)

        if user_list == "":
            user_list = "None"

        await interaction.response.send_message(f"## TTS Blacklisted users:\n`{user_list}`")
