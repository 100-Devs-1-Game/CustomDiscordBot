import os
from datetime import datetime, timezone

import discord
from discord import Interaction
from discord.ext import commands
from discord.ui import InputText, Modal
from dotenv import load_dotenv

from databases import Database
from github_wrapper import GithubWrapper
from utils import Utils

load_dotenv()
TEST_CHANNEL_ID = int(os.getenv("TEST_CHANNEL_ID", "0"))


class Game(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    group = discord.SlashCommandGroup("game", "Game channel commands")

    @group.command(
        description="Show information about the game associated with this channel"
    )
    async def info(self, ctx: discord.ApplicationContext):
        game_info = (
            Database.get_default_game_info()
            if Utils.is_test_environment()
            else Database.get_game_info(ctx.channel.id)
        )
        if not game_info:
            await ctx.respond("No game info found for this channel.", ephemeral=True)
            return

        await Game.send_game_info(ctx, game_info)

    @group.command(description="Set or update the description for your game")
    async def setdescription(self, ctx: discord.ApplicationContext):
        game_info = (
            Database.get_default_game_info()
            if Utils.is_test_environment()
            else Database.get_game_info(ctx.channel.id)
        )
        if not game_info:
            await ctx.respond("No game associated with this channel.", ephemeral=True)
            return

        if ctx.author.name != game_info["owner"]:
            await ctx.respond(
                "Only the game owner can update the description.", ephemeral=True
            )
            return

        current_desc = game_info.get("description", "")
        modal = DescriptionModal(game_info["id"], current_desc)
        await ctx.send_modal(modal)

    @group.command(description="Set the itch.io link for your game")
    async def setitchiolink(self, ctx: discord.ApplicationContext, link: str):
        game_info = (
            Database.get_default_game_info()
            if Utils.is_test_environment()
            else Database.get_game_info(ctx.channel.id)
        )
        if not game_info:
            await ctx.respond("No game associated with this channel.", ephemeral=True)
            return

        if not ctx.author.guild_permissions.manage_guild:
            await ctx.respond(
                "Only moderators can update the itch.io link.", ephemeral=True
            )
            return

        Database.update_field(
            Database.GAMES_DB, "games", game_info["id"], "itch_io_link", link
        )
        await ctx.respond("Itch.io link updated.", ephemeral=True)

    @group.command(
        description="Builds executables and deploys the HTML export to itch.io"
    )
    async def build(self, ctx: discord.ApplicationContext):
        game_info = (
            Database.get_default_game_info()
            if Utils.is_test_environment()
            else Database.get_game_info(ctx.channel.id)
        )
        if not game_info:
            await ctx.respond("No game associated with this channel.", ephemeral=True)
            return

        if ctx.author.name != game_info["owner"]:
            await ctx.respond(
                "Only the game owner can trigger a build.", ephemeral=True
            )
            return

        # await ctx.defer(ephemeral=True)  # immediately tells Discord "working on it"

        g = GithubWrapper.get_github()
        repo_url = "100-Devs-1-Game/" + game_info["repo_name"]
        print("Fetching repo:", repo_url)
        repo = g.get_repo(repo_url)

        if not repo:
            await ctx.respond("Could not find the repository.", ephemeral=True)
            return

        await ctx.respond(f"Building new release for {repo.url}", ephemeral=True)

        sha = repo.get_branch("main").commit.sha

        # base tag = YYYY.MM.DD
        today = datetime.now(timezone.utc).strftime("%Y.%m.%d")
        base_tag = f"v{today}"

        # fetch existing tags
        tags = [t.name for t in repo.get_tags()]

        # ensure uniqueness for today
        matches = [t for t in tags if t.startswith(base_tag)]
        if not matches:
            new_tag = base_tag
        else:
            counters = []
            for m in matches:
                parts = m.split("-")
                if len(parts) > 1 and parts[1].isdigit():
                    counters.append(int(parts[1]))
            next_counter = max(counters, default=0) + 1
            new_tag = f"{base_tag}-{next_counter}"

        # create tag object + ref
        tag = repo.create_git_tag(
            tag=new_tag, message=f"Release {new_tag}", object=sha, type="commit"
        )
        repo.create_git_ref(ref=f"refs/tags/{new_tag}", sha=tag.sha)

        print(f"{repo.url} Created tag: {new_tag}")

    @group.command(
        description="Make the owner of this game an itchio admin for their page"
    )
    async def makeitchioadmin(self, ctx: discord.ApplicationContext, link: str):
        if not Utils.is_admin(ctx.author):
            await ctx.respond("❌ You do not have permission to use this command.")
            return

        game_info = (
            Database.get_default_game_info()
            if Utils.is_test_environment()
            else Database.get_game_info(ctx.channel.id)
        )

        if not game_info:
            await ctx.respond("⚠️ No game found for this channel.", ephemeral=True)
            return

        owner = Utils.get_member_by_name(ctx.guild, game_info["owner"])
        # direct message the owner with the link
        if owner:
            try:
                await owner.send(
                    f"Hello {owner.display_name},\n\n"
                    f"You have been made an admin for the itch.io page of your game '{game_info['name']}'.\n"
                    f"Please visit the following link to manage your game's page:\n{link}\n\n"
                    "Best regards,\nThe Godot Collaborative Game Jam Team"
                )
            except discord.Forbidden:
                await ctx.respond(
                    f"⚠️ Could not send DM to {owner.display_name}. They might have DMs disabled.",
                    ephemeral=True,
                )
                return

        await ctx.respond(f"✅ Invite sent to {owner.display_name}", ephemeral=True)

    @group.command(description="Get the itch.io link of the owner of this game")
    async def getowneritchiolink(self, ctx: discord.ApplicationContext):
        game_info = (
            Database.get_default_game_info()
            if Utils.is_test_environment()
            else Database.get_game_info(ctx.channel.id)
        )

        if not game_info:
            await ctx.respond("⚠️ No game found for this channel.", ephemeral=True)
            return

        owner = ctx.guild.get_member_named(game_info["owner"])

        contributor = Database.fetch_one_as_dict(
            Database.GAMES_DB,
            "contributors",
            "discord_username = ?",
            (owner.name,),
        )

        if not contributor:
            await ctx.channel.send(
                f"⚠️ {owner.mention} please register as a contributor on our server ( `/contributors register` ).\nYou can react with ✅ to this message when you are done."
            )

            await ctx.respond(
                f"⚠️ No contributor info found for {owner.display_name}.",
                ephemeral=True,
            )
            return

        owner_itchio_link = contributor.get("itch_io_link", "")

        if not owner_itchio_link:
            await ctx.channel.send(
                f"⚠️ {owner.mention} please add a link to your itch.io account ( `/contributors updateitchiolink` ) so you can be made an admin on your games page.\nYou can react with ✅ to this message when you are done."
            )
            await ctx.respond(
                f"⚠️ No itch.io link found for {owner.display_name}.",
                ephemeral=True,
            )
            return

        await ctx.respond(
            f"✅ {owner.display_name}'s itch.io link: `{owner_itchio_link}`",
            ephemeral=True,
        )

    @staticmethod
    async def send_game_info(ctx, game_info):
        description = game_info.get("description", "")
        if not description:
            description = (
                "No description provided. Use `/game setdescription` to add one."
            )

        embed = discord.Embed(
            title=game_info["name"],
            description=description,
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Repository",
            value=f"[GitHub Link]({GithubWrapper.GITHUB_URL_PREFIX + game_info['repo_name']})",
            inline=False,
        )
        embed.add_field(name="Owner", value=game_info["owner_display_name"])

        rows = Game.fetch_contributors(game_info, "discord_display_name")
        if rows:
            contributors_str = "\n".join(f"**{name}** — {role}" for name, role in rows)
        else:
            contributors_str = "No contributors registered."

        embed.add_field(name="Contributors", value=contributors_str, inline=False)

        await ctx.respond(embed=embed, ephemeral=True)

    @staticmethod
    def get_channel_id(game_info: dict) -> int:
        if Utils.is_test_environment():
            return TEST_CHANNEL_ID
        else:
            return game_info["channel_id"]

    @staticmethod
    def fetch_contributors(game_info: dict, name="credit_name"):
        return Database.execute(
            Database.GAMES_DB,
            f"""
			SELECT c.{name}, gc.role
			FROM game_contributors gc
			JOIN contributors c ON c.id = gc.contributor_id
			WHERE gc.game_id = ?
		""",
            (game_info["id"],),
        )


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
            value=current_description,  # pre-fill with existing description
        )

        self.add_item(self.description_input)

    async def callback(self, interaction: Interaction):
        print("Description Modal submitted")
        new_description = self.description_input.value

        Database.update_field(
            Database.GAMES_DB, "games", self.game_id, "description", new_description
        )

        await interaction.response.send_message(
            f"Description updated for game ID {self.game_id}.", ephemeral=True
        )
