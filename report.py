import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils import Utils

Utils.ensure_env_var("REPORT_CHANNEL_ID", "1434093367385522267")  # Test server

load_dotenv()
REPORT_CHANNEL_ID = int(os.getenv("REPORT_CHANNEL_ID", "0"))


class Report(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    group = discord.SlashCommandGroup("report", "Report to moderators")

    @group.command(description="Report user to moderators for using DMs")
    async def dm(self, ctx: discord.ApplicationContext, user: discord.User):
        await ctx.respond(f"Reported {user.mention} for using DMs.", ephemeral=True)
        mod_channel = self.bot.get_channel(REPORT_CHANNEL_ID)

        # hash user name of sender to anonymize
        user_hash = hash(user.name)

        if mod_channel:
            await mod_channel.send(
                f"Anonymous user {user_hash} reported {user.mention} for using DMs."
            )
