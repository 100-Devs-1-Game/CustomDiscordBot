# Required packages
# pip install py-cord
# pip install "pyjwt[crypto]"

import discord
import os
import time
import jwt
from dotenv import load_dotenv
import requests

GUILD_IDS = [1393033395298373643]  # your server IDs

# GitHub App credentials
APP_ID = os.getenv("GITHUB_APP_ID")              # GitHub App ID
PRIVATE_KEY_PATH = "100devs-discord-bot.2025-08-26.private-key.pem"  # downloaded private key
INSTALLATION_ID = os.getenv("GITHUB_INSTALLATION_ID")  # App installation ID for the repo/org
REPO_OWNER = "100-Devs-1-Game"
REPO_NAME = "ProjectTemplate"


load_dotenv() # load all the variables from the env file
bot = discord.Bot()



# A decorator to create guild-specific slash commands
def guild_slash_command(**kwargs):
	kwargs['guild_ids'] = GUILD_IDS
	return bot.slash_command(**kwargs)


def create_jwt():
    with open("100devs-discord-bot.2025-08-26.private-key.pem", "r") as f:
        private_key = f.read()
    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,  # max 10 min
        "iss": APP_ID                  # integer, not string
    }
    token = jwt.encode(payload, private_key, algorithm="RS256")
    return token


def get_installation_token():
    """Exchange JWT for an installation token."""
    jwt_token = create_jwt()
    url = f"https://api.github.com/app/installations/{INSTALLATION_ID}/access_tokens"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    return response.json()["token"]


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


@bot.slash_command(name="create_issue", description="Create a GitHub issue")
async def create_issue(ctx: discord.ApplicationContext, title: str, body: str = ""):
    try:
        token = get_installation_token()
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json"
        }
        data = {"title": title, "body": body}
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        issue_url = response.json()["html_url"]
        await ctx.respond(f"Issue created! {issue_url}")
    except requests.HTTPError as e:
        await ctx.respond(f"Failed to create issue: {e.response.text}")


bot.run(os.getenv('TOKEN')) # run the bot with the token