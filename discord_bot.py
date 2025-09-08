import os
from pathlib import Path

import discord
from dotenv import load_dotenv
from github import Auth, Github

from assets import Assets
from contributors import Contributors
from fun import Fun
from game import Game
from game_channel import GameChannel
from help import Help
from onboarding import Onboarding
from potato import Potato

# load all the variables from the env file
load_dotenv()

GUILD_IDS = [int(os.getenv("GUILD_ID"))]  # your server IDs

# GitHub App credentials
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")  # GitHub App ID
PRIVATE_KEY_PATH = Path(
    "100devs-discord-bot.2025-08-26.private-key.pem"  # downloaded private key
)
GITHUB_INSTALLATION_ID = os.getenv(
    "GITHUB_INSTALLATION_ID"
)  # App installation ID for the repo/org
REPO_OWNER = "100-Devs-1-Game"
REPO_NAME = "ProjectTemplate"

assert GITHUB_APP_ID
assert GITHUB_INSTALLATION_ID

appauth = Auth.AppAuth(GITHUB_APP_ID, PRIVATE_KEY_PATH.read_text())
installauth = appauth.get_installation_auth(int(GITHUB_INSTALLATION_ID))

GITHUB = Github(auth=installauth)

bot = discord.Bot(intents=discord.Intents.all())


# A decorator to create guild-specific slash commands
def guild_slash_command(**kwargs):
    kwargs["guild_ids"] = GUILD_IDS
    return bot.slash_command(**kwargs)


@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")


@guild_slash_command(name="hello", description="Say hello to the bot")
async def hello(ctx: discord.ApplicationContext):
    await ctx.respond("Hey!")


@guild_slash_command(
    name="lintorder", description="Display the order our gdlinter expects"
)
async def lintorder(ctx: discord.ApplicationContext):
    BASE_DIR = os.path.dirname(
        os.path.abspath(__file__)
    )  # folder where your bot script is
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
        color=discord.Color.blue(),
    )

    await ctx.respond(embed=embed)


@bot.slash_command(name="create_issue", description="Create a GitHub issue")
async def create_issue(ctx: discord.ApplicationContext, title: str, body: str = ""):
    created_issue = GITHUB.get_repo(f"{REPO_OWNER}/{REPO_NAME}").create_issue(
        title, body
    )
    issue_url = created_issue.html_url
    await ctx.respond(f"Issue created! {issue_url}", ephemeral=True)


if __name__ == "__main__":
    bot.add_cog(Potato(bot))
    bot.add_cog(Fun(bot))
    bot.add_cog(Help(bot))
    bot.add_cog(Onboarding(bot))
    # bot.add_cog(GoogleDrive(bot))
    bot.add_cog(GameChannel(bot))
    bot.add_cog(Game(bot))
    bot.add_cog(Contributors(bot))
    bot.add_cog(Assets(bot))

    bot.run(os.getenv("TOKEN"))  # run the bot with the token
