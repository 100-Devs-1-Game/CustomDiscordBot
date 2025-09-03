import discord
from discord.ext import commands
from databases import Database
from game import Game
from utils import Utils
import os
from dotenv import load_dotenv


load_dotenv()
GUILD_ID = [int(os.getenv("GUILD_ID"))]



class Assets(commands.Cog):
	ASSET_TYPES = [ "2D Art", "3D Art", "SFX", "Music", "Voice", "Narrative" ]
	
	def __init__(self, bot: discord.Bot):
		self.bot = bot

	group = discord.SlashCommandGroup("assets", "Assets commands")	

	@group.command(description="Request an asset for your game from your game channel")
	async def request(self, ctx: discord.ApplicationContext):
		game_info = Database.get_default_game_info() if Utils.is_test_environment() else Database.get_game_info(ctx.channel.id)
		if not game_info:
			await ctx.respond("⚠️ No game found for this channel.", ephemeral=True)
			return

		if ctx.author.display_name not in game_info["owner"]:
			await ctx.respond("❌ Only the game owner can request assets.", ephemeral=True)
			return

		view = AssetSelectView(self.ASSET_TYPES, game_info, action="request")
		await ctx.respond("Pick an asset type to request:", view=view, ephemeral=True)


	@group.command(description="List all pending asset requests")
	async def listrequests(self, ctx: discord.ApplicationContext):
		view = AssetSelectView(self.ASSET_TYPES, {}, action="list")
		await ctx.respond("Pick an asset type to list requests:", view=view, ephemeral=True)


	@group.command(description="List all asset requests that you have accepted")
	async def listaccepted(self, ctx: discord.ApplicationContext):
		view = AssetSelectView(self.ASSET_TYPES, {}, action="list", user= str(ctx.author))
		await ctx.respond("Pick an asset type to list requests:", view=view, ephemeral=True)



class AssetRequestModal(discord.ui.Modal):
	def __init__(self, asset_type: str, game_info: dict):
		super().__init__(title=f"Asset Request: {asset_type}")
		self.asset_type = asset_type
		self.game_info = game_info

		self.add_item(discord.ui.InputText(
			label="Content",
			style=discord.InputTextStyle.long,
			placeholder="Describe the asset..."
		))

		self.add_item(discord.ui.InputText(
			label="Context (optional)",
			style=discord.InputTextStyle.singleline,
			required=False
		))


	async def callback(self, interaction: discord.Interaction):
		content = self.children[0].value
		context = self.children[1].value if self.children[1].value else "N/A"

		Database.add_asset_request(
			game_id=self.game_info["id"],
			asset_type=self.asset_type,
			content=content,
			context=context,
			requested_by=str(interaction.user)
		)

		await interaction.response.send_message(
			f"**Asset Request Submitted**\n"
			f"Type: {self.asset_type}\n"
			f"Content: {content}\n"
			f"Context: {context}",
			#ephemeral=True
		)



class AssetTypeSelect(discord.ui.Select):
	def __init__(self, asset_types: list[str], game_info: dict, action: str, user= None):
		options = [discord.SelectOption(label=a, value=a) for a in asset_types]
		super().__init__(placeholder="Select asset type...", options=options)
		self.game_info = game_info
		self.action = action  # "request" or "list"
		self.user = user


	async def callback(self, interaction: discord.Interaction):
		if self.action == "request":
			modal = AssetRequestModal(self.values[0], self.game_info)
			await interaction.response.send_modal(modal)
		
		elif self.action == "list":
			asset_type = self.values[0]
			if self.user:
				rows = Database.get_asset_requests_by_type(asset_type, "Accepted", self.user)
			else:
				rows = Database.get_asset_requests_by_type(asset_type)
			
			if not rows:
				await interaction.response.send_message(
					f"No requests for {asset_type}.", ephemeral=True
				)
				return

			first= True
			for req in rows:
				request_id = req["id"]
				content = req["content"]
				context = req["context"] or "N/A"
				channel_id = Database.get_game_channel(req["game_id"])

				embed = discord.Embed(
					title=f"{content}",
					description=f"**Context:** {context}",  #\n**Requested By:** {req['requested_by']}",
					color=discord.Color.blurple()
				)

				if self.user:
					view = FinishView(req, Database.get_game_info(channel_id))
				else:
					view = RequestView(req, Database.get_game_info(channel_id))
					
				if first:
					await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
					first= False
				else:
					await interaction.followup.send(embed=embed, view=view, ephemeral=True)	



class AssetSelectView(discord.ui.View):
	def __init__(self, asset_types: list[str], game_info: dict, action: str, user= None):
		super().__init__()
		self.add_item(AssetTypeSelect(asset_types, game_info, action, user))



class AcceptButton(discord.ui.Button):
	def __init__(self, request: dict, game_info: dict):
		super().__init__(label="Accept", style=discord.ButtonStyle.success)
		self.request = request
		self.game_info = game_info


	async def callback(self, interaction: discord.Interaction):
		Database.mark_request_accepted(self.request["id"], str(interaction.user))
		
		channel = interaction.client.get_channel(Game.get_channel_id(self.game_info))
		await channel.send(
			f"👷 Asset request **{self.request['content']}** accepted by {interaction.user.mention}"
		)

		await interaction.response.send_message(
			f"👷 You accepted the asset request *{self.request['content']}**", ephemeral=True
		)



class FinishButton(discord.ui.Button):
	def __init__(self, request: dict, game_info: dict):
		super().__init__(label="Finished", style=discord.ButtonStyle.success)
		self.request = request
		self.game_info = game_info


	async def callback(self, interaction: discord.Interaction):
		Database.mark_request_finished(self.request["id"])
		
		channel = interaction.client.get_channel(Game.get_channel_id(self.game_info))
		await channel.send(
			f"✅  Asset request **{self.request['content']}** finished by {interaction.user.mention}"
		)

		await interaction.response.send_message(
			f"✅ You finished the request **{self.request['content']}**", ephemeral=True
		)



class RequestView(discord.ui.View):
	def __init__(self, request, game_info: dict):
		super().__init__()
		self.add_item(AcceptButton(request, game_info))
		self.add_item(discord.ui.Button(
			label=f"Go to {game_info['name']}",
			style=discord.ButtonStyle.link,
			url=f"https://discord.com/channels/{GUILD_ID}/{game_info['channel_id']}"
		))



class FinishView(discord.ui.View):
	def __init__(self, request, game_info: dict):
		super().__init__()
		self.add_item(FinishButton(request, game_info))
		self.add_item(discord.ui.Button(
			label=f"Go to {game_info['name']}",
			style=discord.ButtonStyle.link,
			url=f"https://discord.com/channels/{GUILD_ID}/{game_info['channel_id']}"
		))