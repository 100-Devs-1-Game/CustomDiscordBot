import discord
from discord.ext import commands


class Fun(commands.Cog):
	def __init__(self, bot: discord.Bot):
		self.bot = bot

	@discord.slash_command()
	async def fun(self, ctx: discord.ApplicationContext):
		await ctx.respond("Yes we are having fun!")