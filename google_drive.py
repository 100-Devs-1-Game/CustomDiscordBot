import discord
from discord.ext import commands

# You still have to create the respective command function below for each link!!
LINKS = {
	"art": "https://drive.google.com/drive/folders/1LfAhA14hJT42LL58MhpM5OovNa4l8pFo?usp=drive_link",
	"audio": "https://drive.google.com/drive/folders/1rxDfrA-vUVckwQpiNux61o-XYma4P7HE?usp=drive_link",
	"planning": "https://docs.google.com/document/d/1JvN2SYmeQfQydavLlTtQo-R1JyeDV0DjHk9DZMlqpFg/edit?usp=drive_link",
}



class GoogleDrive(commands.Cog):
	def __init__(self, bot: discord.Bot):
		self.bot = bot

	group = discord.SlashCommandGroup("googledrive", "Google Drive document links")

	@group.command()
	async def art(self, ctx: discord.ApplicationContext):
		await respond_with_link(ctx, "art")

	@group.command()
	async def audio(self, ctx: discord.ApplicationContext):
		await respond_with_link(ctx, "audio")

	@group.command()
	async def planning(self, ctx: discord.ApplicationContext):
		await respond_with_link(ctx, "planning")


async def respond_with_link(ctx, key: str):
	await ctx.respond(f"Here’s the link: {LINKS[key]}", ephemeral=True)