import discord
from discord.ext import commands


class Potato(commands.Cog):
    POTATOES: list[str] = [
        "bake",
        "baked",
        "potat",
        "potato",
        "potatoes",
        "potatos",
        "potato's",
        "tato",
        "tatos",
        "tato's",
    ]

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        for word in self.POTATOES:
            if f"{word}" in message.content:
                await message.add_reaction("🥔")
