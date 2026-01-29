import os
from datetime import datetime, timezone
from enum import IntEnum

import discord
from discord import Interaction
from discord.ext import commands
from discord.ui import InputText, Modal
from dotenv import load_dotenv

from databases import Database
from github_wrapper import GithubWrapper
from utils import Utils


class GameState(IntEnum):
    IN_PROGRESS = 0
    RELEASED = 1
    KEEP_DEVELOPING = 2
    CANCELLED = 3


Utils.ensure_env_var("QA_CHANNEL_ID", "1416625126136483890")  # Test server
Utils.ensure_env_var("SCHEDULE_CHANNEL_ID", "1416666323831885905")  # Test server
load_dotenv()

TEST_CHANNEL_ID = int(os.getenv("TEST_CHANNEL_ID", "0"))
ITCHIO_REQUEST_CHANNEL_ID = 1415533889891598336
QA_CHANNEL_ID = int(os.getenv("QA_CHANNEL_ID"))
SCHEDULE_CHANNEL_ID = int(os.getenv("SCHEDULE_CHANNEL_ID", "0"))


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

    @group.command(description="Get a list of all games under development")
    async def list(self, ctx: discord.ApplicationContext):
        games: list[dict] = Database.fetch_all_as_dict_arr(
            Database.GAMES_DB,
            "games",
        )

        games = [game for game in games if game["state"] == GameState.IN_PROGRESS]
        await Game.send_games_list(ctx, games)

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

    @group.command(description="Set the repository name for your game")
    async def setreponame(self, ctx: discord.ApplicationContext, repo_name: str):
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
                "Only moderators can update the repository name.", ephemeral=True
            )
            return

        Database.update_field(
            Database.GAMES_DB, "games", game_info["id"], "repo_name", repo_name
        )
        await ctx.respond("Repository name updated.", ephemeral=True)

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

        if (
            ctx.author.name != game_info["owner"]
            and not Game.is_contributor(ctx, game_info)
            and not ctx.author.guild_permissions.manage_guild
        ):
            await ctx.respond(
                "Only the game owner or a contributor can trigger a build.",
                ephemeral=True,
            )
            return

        await ctx.defer(ephemeral=True)  # immediately tells Discord "working on it"

        g = GithubWrapper.get_github()
        repo_url = "100-Devs-1-Game/" + game_info["repo_name"]
        print("Fetching repo:", repo_url)
        repo = g.get_repo(repo_url)

        if not repo:
            await ctx.followup.send("Could not find the repository.", ephemeral=True)
            return

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

        await ctx.followup.send(
            f"Building new release for <{repo.html_url}>", ephemeral=True
        )

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

    @group.command(
        description="Request to get admin ( and contributor ) access to the itch.io page of this game"
    )
    async def requestitchio(self, ctx: discord.ApplicationContext):
        game_info = (
            Database.get_default_game_info()
            if Utils.is_test_environment()
            else Database.get_game_info(ctx.channel.id)
        )
        if not game_info:
            await ctx.respond("No game associated with this channel.", ephemeral=True)
            return

        if ctx.author.name != game_info["owner"] and not Game.is_contributor(
            ctx, game_info
        ):
            await ctx.respond(
                "Only the game owner or a contributor can request access.",
                ephemeral=True,
            )
            return

        contributor = Database.fetch_one_as_dict(
            Database.GAMES_DB,
            "contributors",
            "discord_username = ?",
            (ctx.author.name,),
        )

        if not contributor:
            await ctx.respond(
                "Please register as a contributor first using `/contributors register`.",
                ephemeral=True,
            )
            return

        itchio_account = contributor.get("itch_io_link", "")

        if not itchio_account:
            await ctx.respond(
                "You need to have an itch.io account for this to work."
                "\nIf you already have one or have successfully created a new one use `/contributors updateitchiolink` to update it in your contributors profile.",
                ephemeral=True,
            )
            return

        request_channel = ctx.guild.get_channel(ITCHIO_REQUEST_CHANNEL_ID)
        if not request_channel:
            await ctx.respond("Request channel not found.", ephemeral=True)
            return

        itch_io_link = game_info.get("itch_io_link", "")

        if not itch_io_link:
            await request_channel.send(
                f"⚠️ The game '{game_info['name']}' does not have an itch.io link set. Please set it using `/game setitchiolink`."
            )

        await request_channel.send(
            f"User {ctx.author.mention} has requested admin access to the itch.io page for the game '{game_info['name']}'.\n"
            f"Game Owner: {game_info['owner_display_name']}\n"
            f"Itch.io Page: <{itch_io_link}>\n"
            f"Users itch.io link: <{itchio_account}>\n",
            allowed_mentions=discord.AllowedMentions.none(),
        )

        await ctx.respond(
            "✅ Request sent. It has to be processed by a moderator and you'll receive a DM once it's done."
            " On the itch.io page click 'Edit Game', then choose 'More'->'Admins' and check 'Display as contributor' next to your name to make the game part of your portfolio.",
            ephemeral=True,
        )

    @group.command(description="Remove all pending requests for this game")
    async def removerequests(self, ctx: discord.ApplicationContext):
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

        Database.remove_asset_requests_for_game(game_info["id"])

        await ctx.defer()

        # Remove all messages from channels that contain links to the games channel
        await Utils.purge_messages_with_game_channel_link(
            ctx.guild,
            [
                int(
                    os.getenv("ANNOUNCE_CHANNEL_ID", 0)
                ),  # Asset request announce channel
                int(os.getenv("CONTRIBUTORS_REQUEST_CHANNEL_ID", 0)),
            ],
            game_info["channel_id"],
        )
        await ctx.respond(
            "All pending requests for this game have been removed.", ephemeral=True
        )

    @group.command(description="Request game testing for your latest build")
    async def test(self, ctx: discord.ApplicationContext, instructions: str = ""):
        game_info = (
            Database.get_default_game_info()
            if Utils.is_test_environment()
            else Database.get_game_info(ctx.channel.id)
        )
        if not game_info:
            await ctx.respond("No game associated with this channel.", ephemeral=True)
            return

        if ctx.author.name != game_info["owner"] and not Game.is_contributor(
            ctx, game_info
        ):
            await ctx.respond(
                "Only the game owner or a contributor can request testing.",
                ephemeral=True,
            )
            return

        await ctx.defer(ephemeral=True)

        request_channel = ctx.guild.get_channel(QA_CHANNEL_ID)
        if not request_channel:
            await ctx.respond("Request channel not found.", ephemeral=True)
            return

        role = discord.utils.get(ctx.interaction.guild.roles, name="PingTester")
        instructions_text = instructions if instructions else "---"
        itchio_link = game_info.get("itch_io_link", "")
        itchio_text = f"<{itchio_link}> ( Pw: *100devs* )" if itchio_link else "---"

        await request_channel.send(
            f"User *{ctx.author.display_name}* has requested testing for the game <#{game_info['channel_id']}>."
            f"\nGithub releases: <{GithubWrapper.GITHUB_URL_PREFIX + game_info['repo_name'] + '/releases'}>"
            f"\nItchio page: {itchio_text}"
            f"\nInstructions: {instructions_text}"
            f"\n{role.mention} post your feedback in this thread 👇",
            allowed_mentions=discord.AllowedMentions(roles=True),
        )

        # create a channel thread from that last posted message
        last_message = await request_channel.history(limit=1).flatten()
        if last_message:
            thread = await last_message[0].create_thread(
                name=f"Testing {game_info['name']}"
            )

            await thread.send(f"{ctx.author.mention} Feedback thread created.")

            await thread.send(
                "Testers: Please post your feedback here."
                "\nMake sure to mention the platform you tested on (Windows, Mac, Linux, Web)."
                "\nAnd the version you tested, if applicable ( may not be available for Web )."
            )

        await ctx.respond(
            "✅ A request for testing has been added.",
            ephemeral=True,
        )

    @group.command(
        description="List all contributors to this game along with their itch.io links (if provided)"
    )
    async def listcontributorsitchio(self, ctx: discord.ApplicationContext):
        game_info = (
            Database.get_default_game_info()
            if Utils.is_test_environment()
            else Database.get_game_info(ctx.channel.id)
        )
        if not game_info:
            await ctx.respond("No game associated with this channel.", ephemeral=True)
            return

        # respond with a list of contributors and their itch.io links
        contributors = Database.execute(
            Database.GAMES_DB,
            """
            SELECT c.discord_display_name, c.itch_io_link
            FROM game_contributors gc
            JOIN contributors c ON c.id = gc.contributor_id
            WHERE gc.game_id = ?
        """,
            (game_info["id"],),
        )
        if not contributors:
            await ctx.respond("No contributors found for this game.", ephemeral=True)
            return
        lines = []
        for name, link in contributors:
            if link:
                lines.append(f"**{name}**: <{link}>")
            else:
                lines.append(f"**{name}**: No itch.io link provided.")
        response = "\n".join(lines)
        await ctx.respond(response, ephemeral=True)

    @group.command(description="Set new game owner")
    async def setowner(self, ctx: discord.ApplicationContext, user: discord.User):
        game_info = (
            Database.get_default_game_info()
            if Utils.is_test_environment()
            else Database.get_game_info(ctx.channel.id)
        )
        if not game_info:
            await ctx.respond("No game associated with this channel.", ephemeral=True)
            return

        if (
            ctx.author.name != game_info["owner"]
            and not ctx.author.guild_permissions.manage_guild
        ):
            await ctx.respond(
                "Only the game owner or mods can set the new owner.",
                ephemeral=True,
            )
            return

        # Update the game owner in the database using helper to ensure proper DB handling
        Database.update_field(
            Database.GAMES_DB, "games", game_info["id"], "owner", user.name
        )
        # Also update the display name so UIs show the correct owner display name
        Database.update_field(
            Database.GAMES_DB,
            "games",
            game_info["id"],
            "owner_display_name",
            getattr(user, "display_name", user.name),
        )

        await ctx.respond(
            f"Game owner has been updated to {user.mention}.", ephemeral=True
        )

    @group.command(description="Set the link to the Game Design Document")
    async def setgddlink(self, ctx: discord.ApplicationContext, link: str):
        game_info = (
            Database.get_default_game_info()
            if Utils.is_test_environment()
            else Database.get_game_info(ctx.channel.id)
        )
        if not game_info:
            await ctx.respond("No game associated with this channel.", ephemeral=True)
            return

        if (
            ctx.author.name != game_info["owner"]
            and not ctx.author.guild_permissions.manage_guild
        ):
            await ctx.respond(
                "Only the game owner or mods can set the GDD link.",
                ephemeral=True,
            )
            return

        # validate link format (basic check)
        if not (link.startswith("http://") or link.startswith("https://")):
            await ctx.respond(
                "Please provide a valid URL starting with http:// or https://",
                ephemeral=True,
            )
            return

        # turn /edit.. following links into /view.. links for Google Docs
        if "/edit" in link:
            link = link.split("/edit")[0] + "/view"

        # Update the GDD link in the database using helper to ensure proper DB handling
        Database.update_field(
            Database.GAMES_DB, "games", game_info["id"], "gdd_link", link
        )

        await ctx.respond(f"GDD link has been updated to {link}.", ephemeral=True)

    @group.command(description="Update game release state to 'Released'")
    async def released(
        self, ctx: discord.ApplicationContext, keep_developing: bool = False
    ):
        await Game.set_release_state(
            ctx, GameState.KEEP_DEVELOPING if keep_developing else GameState.RELEASED
        )

    @group.command(description="Update game release state to 'Cancelled'")
    async def cancelled(self, ctx: discord.ApplicationContext):
        await Game.set_release_state(ctx, GameState.CANCELLED)

    @staticmethod
    async def set_release_state(ctx: discord.ApplicationContext, state: GameState):
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
                "Only the mods can set game development states.",
                ephemeral=True,
            )
            return

        # Update the game state in the database using helper to ensure proper DB handling
        Database.update_field(
            Database.GAMES_DB, "games", game_info["id"], "state", state.value
        )

        await ctx.respond(
            f"Game state has been updated to {state.name}.", ephemeral=True
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
            name="State",
            value=GameState(game_info["state"]).name.replace("_", " ").title(),
            inline=False,
        )
        embed.add_field(
            name="Repository",
            value=f"[GitHub Link]({GithubWrapper.GITHUB_URL_PREFIX + game_info['repo_name']})",
            inline=False,
        )
        embed.add_field(name="Owner", value=game_info["owner_display_name"])

        if game_info.get("gdd_link"):
            embed.add_field(
                name="Game Design Document",
                value=f"[Google Drive Doc]({game_info['gdd_link']})",
                inline=False,
            )

        if game_info.get("itch_io_link"):
            embed.add_field(
                name="Itch.io Link",
                value=f"[Itch.io Page]({game_info['itch_io_link']})",
                inline=False,
            )

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

    @staticmethod
    def is_contributor(ctx: discord.ApplicationContext, game_info: dict) -> bool:
        contributor = Database.fetch_one_as_dict(
            Database.GAMES_DB,
            "contributors",
            "discord_username = ?",
            (ctx.author.name,),
        )
        if not contributor:
            return False

        role = Database.fetch_one_as_dict(
            Database.GAMES_DB,
            "game_contributors",
            "game_id = ? AND contributor_id = ?",
            (game_info["id"], contributor["id"]),
        )
        return role is not None

    @staticmethod
    async def send_games_list(ctx, games):
        embeds = []
        buffer = ""
        field_name = "Games"

        for game in games:
            github_link = GithubWrapper.GITHUB_URL_PREFIX + game.get("repo_name")
            itchio_link = game.get("itch_io_link")
            channel_id = game.get("channel_id")
            gameid = f"{(game.get('id')):02}"

            line = f"`{gameid}` "
            line += f"[GitHub]({github_link}) | "

            if isinstance(itchio_link, str) and itchio_link != "":
                line += f"[ItchIO]({itchio_link}) | "
            else:
                line += "ItchIO | "

            line += f"<#{channel_id}>"
            line += "\n"

            if len(buffer) + len(line) > 1024:
                embed = discord.Embed(
                    title="List of games",
                    color=discord.Color.blurple(),
                )
                embed.add_field(name=field_name, value=buffer.rstrip(), inline=False)
                embeds.append(embed)
                buffer = ""

            buffer += line

        if buffer:
            embed = discord.Embed(
                title="List of games",
                color=discord.Color.blurple(),
            )
            embed.add_field(name=field_name, value=buffer.rstrip(), inline=False)
            embeds.append(embed)

        # Send embeds: first as response, rest as followups
        if embeds:
            await ctx.respond(embed=embeds[0], ephemeral=True)
            for embed in embeds[1:]:
                await ctx.followup.send(embed=embed, ephemeral=True)


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
