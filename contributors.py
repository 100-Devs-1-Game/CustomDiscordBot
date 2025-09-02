import discord
from discord.ext import commands
from discord import Interaction
from discord.ui import Modal, InputText
from databases import Database


CONTRIBUTION_TYPES = [ "Programmer", "2D Artist", "3D Artist", "Composer", "Sound Designer", "Writer", "Voice Actor"]


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


	@group.command()
	async def add(self, ctx: discord.ApplicationContext, member: discord.Member):
		game_info = Database.get_game_info(ctx.channel.id)
		if not game_info:
			await ctx.respond("⚠️ No game found for this channel.", ephemeral=True)
			return

		if ctx.author.display_name not in game_info["owner"]:
			await ctx.respond("❌ Only the game owner can add contributors.", ephemeral=True)
			return
		
		contributor = Database.fetch_one_as_dict(
			Database.GAMES_DB,
			"contributors",
			"discord_username = ?",
			(str(member),)
		)

		if not contributor:
			# not registered — tell owner how to get them registered
			await ctx.respond(
				f"{member.display_name} is not registered as a contributor. "
				"Ask them to run `/contributors register`.",
				ephemeral=True
			)
			return

		# show role dropdown
		await ctx.respond(
			f"Select contributors role for **member: {member.display_name}**:",
            view=ContributionRoleView(game_info["id"], contributor["id"]),
            ephemeral=True
        )


	# @group.command()
	# async def test(self, ctx: discord.ApplicationContext, member: discord.Member):
	# 	game_info = Database.fetch_one_as_dict(Database.GAMES_DB, "games", "id = ?", (1, ) )
		
	# 	if not game_info:
	# 		await ctx.respond("⚠️ No game found for this channel.", ephemeral=True)
	# 		return

	# 	if ctx.author.display_name not in game_info["owner"]:
	# 		await ctx.respond("❌ Only the game owner can add contributors.", ephemeral=True)
	# 		return

	# 	contributor = Database.fetch_one_as_dict(
	# 		Database.GAMES_DB,
	# 		"contributors",
	# 		"discord_username = ?",
	# 		(str(member),)
	# 	)

	# 	if not contributor:
	# 		# not registered — tell owner how to get them registered
	# 		await ctx.respond(
	# 			f"{member.display_name} is not registered as a contributor. "
	# 			"Ask them to run `/contributors register`.",
	# 			ephemeral=True
	# 		)
	# 		return

	# 	# show role dropdown
	# 	await ctx.respond(
	# 		f"Select contributors role for **member: {member.display_name}**:",
    #         view=ContributionRoleView(game_info["id"], contributor["id"]),
    #         ephemeral=True
    #     )



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



class ContributionRoleSelect(discord.ui.Select):
	def __init__(self, game_id: int, contributor_id: int):
		self.game_id = game_id
		self.contributor_id = contributor_id

		options = [ discord.SelectOption(label=role, value=role) for role in CONTRIBUTION_TYPES ]
		super().__init__(placeholder="Select contribution type...", min_values=1, max_values=1, options=options )


	async def callback(self, interaction: discord.Interaction):
		chosen_role = self.values[0]

		# Insert link into relation table
		Database.insert_into_db(
			Database.GAMES_DB,
			"game_contributors",
			game_id=self.game_id,
			contributor_id=self.contributor_id,
			role=chosen_role
		)

		await interaction.response.send_message(
			f"✅ Added contributor with role: **{chosen_role}**",
			#ephemeral=True
		)



class ContributionRoleView(discord.ui.View):
	def __init__(self, game_id: int, contributor_id: int, timeout=60):
		super().__init__(timeout=timeout)
		self.add_item(ContributionRoleSelect(game_id, contributor_id))