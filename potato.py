import re
import discord
from discord.ext import commands


class Potato(commands.Cog):
    POTATOES: list[str] = [
        "bake",
        "baked",
        "potat",
        "potato",
        "potatoes",
        "potatoez",
        "potatos",
        "potato's",
        "tato",
        "tatos",
        "tatoz",
        "tato's",
    ]

    def __init__(self, bot: discord.Bot):
        self.bot = bot
        words = "|".join(re.escape(word) for word in self.POTATOES)
        self.pattern = re.compile(rf"\b(?:{words})\b|🥔|:potato:", re.IGNORECASE)
        #print(f"Using potato reaction regex: {self.pattern}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if self.pattern.search(message.content):
            try:
                await message.add_reaction("🥔")
            except Exception as e:
                print(e)
