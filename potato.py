import discord
from discord.ext import commands


class Potato(commands.Cog):
    POTATOES: list[str] = ["baked", "potato", "tato"]

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        print(message.content)
        for word in self.POTATOES:
            if (
                message.content.startswith(word + " ")
                or message.content.endswith(" " + word)
                or f" {word} " in message.content
            ):
                await message.add_reaction("🥔")
