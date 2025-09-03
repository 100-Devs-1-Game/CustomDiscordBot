import discord
from discord.ext import commands


class Help(commands.Cog):
	def __init__(self, bot: discord.Bot):
		self.bot = bot

	group = discord.SlashCommandGroup("help", "Help commands")	

	@group.command(description="Show information about the current channel")
	async def channel(self, ctx: discord.ApplicationContext):
		if isinstance(ctx.channel, discord.TextChannel):
			desc = ctx.channel.topic or "No description set for this channel."
			embed = discord.Embed(
				title=f"#{ctx.channel.name}",
				description=desc,
				color=discord.Color.blue()
			)
		else:
			embed = discord.Embed(
				title="DM Channel",
				description="Direct messages don't have a channel description.",
				color=discord.Color.red()
			)
		await ctx.respond(embed=embed, ephemeral=True)