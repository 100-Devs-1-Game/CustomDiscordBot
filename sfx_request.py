import os

import discord
from discord.ext import commands

from utils import Utils

Utils.ensure_env_var("SFX_REQUEST_CHANNEL_ID", 1461288656169074751)  # Test Server

SFX_REQUEST_CHANNEL = int(os.getenv("SFX_REQUEST_CHANNEL_ID", 0))


class SFXRequests(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.slash_command(description="Request a sound effect")
    async def sfx_request(
        self,
        ctx: discord.ApplicationContext,
        filename: discord.Option(
            str, "Desired filename of the sound effect (no extension)"
        ),
        description: discord.Option(str, "Description of the sound effect"),
        looping: discord.Option(bool, "Should the sound effect loop?", default=False),
        positional: discord.Option(
            bool, "Is the sound effect positional?", default=False
        ),
        variations: discord.Option(
            bool, "Should there be variations of the sound effect?", default=False
        ),
    ):
        if ctx.channel.id == SFX_REQUEST_CHANNEL:
            await ctx.defer(ephemeral=True)
            await ctx.channel.send(
                f"**Filename**: {filename} , **Description**: {description}\n"
                f"**Looping**: {'Yes' if looping else 'No'} , **Positional**: {'Yes' if positional else 'No'} , **Variations**: {'Yes' if variations else 'No'}\n"
            )
        else:
            await ctx.respond("⚠️ Not an SFX request channel.", ephemeral=True)
            return

        # create channel thread for the request
        last_message = await ctx.channel.history(limit=1).flatten()
        if last_message:
            thread = await last_message[0].create_thread(name="Discussion")

            # ping sender in thread
            await thread.send(
                f"{ctx.author.mention} watch this thread for questions about your SFX request!"
            )
        await ctx.followup.send("Request sent!", ephemeral=True)
