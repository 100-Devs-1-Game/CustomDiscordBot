import discord
from discord.ext import commands


class OneHundred(commands.Cog):
    HUNDRED: list[str] = ["100 ", " 100", "100devs"]

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        for word in self.HUNDRED:
            if f"{word}" in message.content:
                await message.add_reaction("💯")
