import discord
import os # default module
from dotenv import load_dotenv

GUILD_IDS = [1393033395298373643]  # your server IDs

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

bot.run(os.getenv('TOKEN')) # run the bot with the token