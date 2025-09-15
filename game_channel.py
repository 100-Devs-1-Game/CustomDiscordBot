import re

import discord
from discord import option
from discord.ext import commands

from databases import Database
from github_wrapper import GithubWrapper
from utils import Utils

FORUM_ID = 1411735698951639193
CHANNEL_CATEGORY = 1411870610279366686
# FORUM_ID = -1
# CHANNEL_CATEGORY =


class GameChannel(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        description="Close Game Idea Thread, Create new Channel for Game, Create Repository on Github"
    )
    @option("game_name", description="Name of game")
    async def create_game(self, ctx: discord.ApplicationContext, game_name: str):
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.respond(
                "You need to run this inside a forum thread.", ephemeral=True
            )
            return
        if (
            FORUM_ID > -1
            and ctx.channel.parent_id != FORUM_ID
            and not Utils.is_test_environment()
        ):
            await ctx.respond(
                "This thread is not part of the correct forum.", ephemeral=True
            )
            return

        if ctx.channel.locked:
            await ctx.respond("This thread is already locked.", ephemeral=True)
            return

        if not ctx.author.guild_permissions.manage_guild:
            await ctx.channel.send(
                f"{ctx.guild.owner.mention} : {ctx.author.mention} requested a game channel for {game_name}. Please approve."
            )
            return

        repo_name_sanitized = sanitize_repo_name(game_name)

        # check if it exists
        existing = None
        for repo in GithubWrapper.get_github_org().get_repos():
            if repo.name.lower() == repo_name_sanitized.lower():
                existing = repo
                break

        if existing:
            print(f"Repo {repo_name_sanitized} already exists: {existing.html_url}")
            await ctx.respond(
                f"Repo {repo_name_sanitized} already exists: {existing.html_url}",
                ephemeral=True,
            )
            return
        else:
            url = ""
            if not Utils.is_test_environment():
                repo = GithubWrapper.get_github_org().create_repo_from_template(
                    repo=GithubWrapper.get_github().get_repo(
                        "100-Devs-1-Game/MinimalProjectTemplate"
                    ),
                    name=repo_name_sanitized,
                    description=f"Repository for the game {game_name} - for 100 Games in 100 Days",
                    private=False,
                    include_all_branches=False,
                )
                url = repo.html_url

        thread = ctx.channel
        guild = ctx.guild
        owner = thread.owner

        category = guild.get_channel(CHANNEL_CATEGORY)

        # create new text channel
        new_channel = await guild.create_text_channel(
            name=game_name,
            topic=f"Copy of {thread.jump_url}\nRepository: {url}\nOwner: {owner.mention}",
            category=category,
        )

        # lock thread
        await thread.edit(
            # archived=True,
            locked=True,
            name=f"[LOCKED] {thread.name}",
        )

        Database.add_game(game_name, repo.name, new_channel.id, owner)

        # add link to new channel in old thread
        await thread.send(f"Thread closed. Continued in {new_channel.mention}")

        await self.copy_messages(thread, new_channel)

        await Utils.send_guide_link(new_channel, owner)

        await new_channel.send(
            f"Here's the automatically created Github Repository: {url}"
        )

    async def copy_messages(self, thread, new_channel):
        async for msg in thread.history(oldest_first=True):
            if msg.author == self.bot.user:
                return
            content = f"**{msg.author.display_name}:** {msg.content}"
            if msg.attachments:
                for att in msg.attachments:
                    content += f"\n{att.url}"
            if content.strip():
                await new_channel.send(
                    content,
                    allowed_mentions=discord.AllowedMentions.none(),
                    silent=True,
                )

    @discord.slash_command(
        description="Copy messages from thread after duplication failed"
    )
    async def debug_copy_messages(
        self, ctx: discord.ApplicationContext, game_name: str
    ):
        await ctx.respond("Not implemented yet.", ephemeral=True)
        return

        if not isinstance(ctx.channel, discord.TextChannel):
            await ctx.respond(
                "You need to run this inside a text channel.", ephemeral=True
            )
            return
        new_channel = ctx.channel

        if new_channel.topic.is_empty():
            await ctx.respond("This channel has no topic.", ephemeral=True)
            return

        # thread_name = parse from topic


def sanitize_repo_name(name: str) -> str:
    # early return if name is already in PascalCase
    if re.fullmatch(r"(?:[A-Z][a-z0-9]*)+", name):
        return name

    name = name.replace("_", " ")
    name = name.replace("-", " ")

    name = re.sub(r"[^a-zA-Z0-9 ]", "", name)
    # split words by spaces, capitalize first letter of each
    words = name.split()
    pascal = "".join(word.capitalize() for word in words)
    return pascal
