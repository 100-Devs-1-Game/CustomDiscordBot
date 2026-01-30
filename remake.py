import discord
from discord.ext import commands


class Remake(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    group = discord.SlashCommandGroup("remake", "Remake Game Jam commands")

    @group.command(
        description="Submit a link to your Remake Game Jam submissions GitHub Repository"
    )
    async def submit(self, ctx: discord.ApplicationContext, link: str):
        await ctx.respond("Command not implemented yet.")
