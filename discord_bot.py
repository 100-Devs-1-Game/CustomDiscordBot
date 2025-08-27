import discord
import os # default module
from dotenv import load_dotenv

GUILD_IDS = [1393033395298373643]  # your server IDs

# A decorator to create guild-specific slash commands
def guild_slash_command(**kwargs):
	kwargs['guild_ids'] = GUILD_IDS
	return bot.slash_command(**kwargs)


load_dotenv() # load all the variables from the env file
bot = discord.Bot()


@bot.event
async def on_ready():
	print(f"{bot.user} is ready and online!")


@guild_slash_command(name="hello", description="Say hello to the bot")
async def hello(ctx: discord.ApplicationContext):
	await ctx.respond("Hey!")


@guild_slash_command(name="lintorder", description="Display the order our gdlinter expects")
async def hello(ctx: discord.ApplicationContext):
	BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # folder where your bot script is
	file_path = os.path.join(BASE_DIR, "linter_order.txt")
	
	if not os.path.exists(file_path):
		await ctx.respond("Bot error: File not found!")
		return

	with open(file_path, "r") as f:
		content = f.read()

	# Discord embeds max description length = 4096 chars
	if len(content) > 4096:
		content = content[:4093] + "..."

	embed = discord.Embed(
		title="GDLint class definition order",
		description=content,
		color=discord.Color.blue()
	)

	await ctx.respond(embed=embed)

bot.run(os.getenv('TOKEN')) # run the bot with the token