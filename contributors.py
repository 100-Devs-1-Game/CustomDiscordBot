import discord
from discord.ext import commands
from discord import Interaction
from discord.ui import Modal, InputText
from databases import Database



class Contributors(commands.Cog):
	def __init__(self, bot: discord.Bot):
		self.bot = bot


	group = discord.SlashCommandGroup("contributors", "Contributor commands")	

	@group.command()
	async def register(self, ctx: discord.ApplicationContext):
		modal = ContributorRegisterModal(
			discord_username=str(ctx.author),
			discord_display_name=ctx.author.display_name,
		)
		await ctx.send_modal(modal)



class ContributorRegisterModal(Modal):
	def __init__(self, discord_username: str, discord_display_name: str | None):
		super().__init__(title="Register as Contributor")
		self.discord_username = discord_username
		self.discord_display_name = discord_display_name

		self.credit_name = InputText(
			label="Credit Name",
			placeholder="Name to display in credits",
			required=True
		)
		self.itch_io_link = InputText(
			label="itch.io Link",
			placeholder="Optional: https://yourgame.itch.io/",
			required=False
		)
		self.alt_link = InputText(
			label="Alternative Link",
			placeholder="Optional: Portfolio, GitHub, etc.",
			required=False
		)

		self.add_item(self.credit_name)
		self.add_item(self.itch_io_link)
		self.add_item(self.alt_link)


	async def callback(self, interaction: discord.Interaction):
		if Database.entry_exists(Database.GAMES_DB, "contributors", "discord_username", self.discord_username):
			await interaction.response.send_message(
				f"⚠️ You are already registered as a Contributor.",
				ephemeral=True
			)
			return

		# Insert new contributor
		Database.register_contributor(
			discord_username=self.discord_username,
			discord_display_name=self.discord_display_name,
			credit_name=self.credit_name.value,
			itch_io_link=self.itch_io_link.value or None,
			alt_link=self.alt_link.value or None,
		)

		await interaction.response.send_message(
			f"✅ Registered as contributor: **{self.credit_name.value}**",
			ephemeral=True
		)
