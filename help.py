import discord
from discord.ext import commands


class Help(commands.Cog):
	def __init__(self, bot: discord.Bot):
		self.bot = bot

	@discord.slash_command()
	async def help(self, ctx: discord.ApplicationContext):
		await ctx.respond("Not implemented yet!")