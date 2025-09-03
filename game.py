import discord
from discord.ext import commands
from databases import Database
from discord import Interaction
from discord.ui import Modal, InputText

from utils import Utils

GITHUB_URL_PREFIX= "https://github.com/100-Devs-1-Game/"


class Game(commands.Cog):
	def __init__(self, bot: discord.Bot):
		self.bot = bot

	group = discord.SlashCommandGroup("game", "100 Games in 100 Days commands")

	@group.command()
	async def info(self, ctx: discord.ApplicationContext):
		game_info = Database.get_default_game_info() if Utils.is_test_environment() else Database.get_game_info(ctx.channel.id)
		if not game_info:
			await ctx.respond("No game info found for this channel.", ephemeral=True)
			return

		await Game.send_game_info(ctx, game_info)


	@group.command()
	async def description(self, ctx: discord.ApplicationContext):
		game_info = Database.get_default_game_info() if Utils.is_test_environment() else Database.get_game_info(ctx.channel.id)
		if not game_info:
			await ctx.respond("No game associated with this channel.", ephemeral=True)
			return

		if ctx.author.name not in game_info["owner"]:
			await ctx.respond("Only the game owner can update the description.", ephemeral=True)
			return

		current_desc = game_info.get("description", "")
		modal = DescriptionModal(game_info["id"], current_desc)
		await ctx.send_modal(modal)


	@staticmethod
	async def send_game_info(ctx, game_info):
		description=game_info.get("description", "")
		if not description:
			description="No description provided. Use `/game description` to add one."
			
		embed = discord.Embed(
			title=game_info["name"],
			description=description,
			color=discord.Color.blurple()
		)
		embed.add_field(name="Repository", value=f"[GitHub Link]({GITHUB_URL_PREFIX + game_info['repo_name']})", inline=False)
		embed.add_field(name="Owner", value=game_info["owner"].split("(", 1)[1].rstrip(")").strip(), inline=True)

		rows= Game.fetch_contributors(game_info)
		if rows:
			contributors_str = "\n".join(f"**{name}** — {role}" for name, role in rows)
		else:
			contributors_str = "No contributors registered."

		embed.add_field(
			name="Contributors",
			value=contributors_str,
			inline=False
		)

		await ctx.respond(embed=embed, ephemeral=True)


	@staticmethod
	def fetch_contributors(game_info):
		return Database.execute(Database.GAMES_DB, """
			SELECT c.discord_display_name, gc.role
			FROM game_contributors gc
			JOIN contributors c ON c.id = gc.contributor_id
			WHERE gc.game_id = ?
		""", (game_info["id"],))



class DescriptionModal(Modal):
	def __init__(self, game_id: int, current_description: str = ""):
		super().__init__(title="Update Game Description")
		self.game_id = game_id

		self.description_input = InputText(
			label="Game Description",
			style=discord.InputTextStyle.paragraph,
			placeholder="Enter a description for your game...",
			required=True,
			max_length=2000,
			value=current_description  # pre-fill with existing description
		)

		self.add_item(self.description_input)


	async def callback(self, interaction: Interaction):
		print("Description Modal submitted")
		new_description = self.description_input.value

		Database.update_field(Database.GAMES_DB, "games", self.game_id, "description", new_description)
		
		await interaction.response.send_message(
			f"Description updated for game ID {self.game_id}.", ephemeral=True
		)


