import discord
from discord.ext import commands
from databases import Database

GITHUB_URL_PREFIX= "https://github.com/100-Devs-1-Game/"


class Game(commands.Cog):
	def __init__(self, bot: discord.Bot):
		self.bot = bot

	group = discord.SlashCommandGroup("game", "100 Games in 100 Days commands")

	@group.command()
	async def info(self, ctx: discord.ApplicationContext):
		game_info = Database.get_game_info(ctx.channel.id)
		if not game_info:
			await ctx.respond("No game info found for this channel.", ephemeral=True)
			return

		await Game.send_game_info(ctx, game_info)


	# @group.command()
	# async def test(self, ctx: discord.ApplicationContext):
	# 	game_info = Database.fetch_one_as_dict("dbs/games.db", "games", "id = ?", (1, ) )
	# 	if not game_info:
	# 		await ctx.respond("No game info found", ephemeral=True)
	# 		return
	# 	await Game.send_game_info(ctx, game_info)


	@staticmethod
	async def send_game_info(ctx, game_info):
		embed = discord.Embed(
			title=game_info["name"],
			description=game_info.get("description", "No description available."),
			color=discord.Color.blurple()
		)
		embed.add_field(name="Repository", value=f"[GitHub Link]({GITHUB_URL_PREFIX + game_info['repo_name']})", inline=False)
		embed.add_field(name="Owner", value=game_info["owner"].split("(", 1)[1].rstrip(")").strip(), inline=True)
		embed.set_footer(text="Game Info Bot")

		await ctx.send(embed=embed)
