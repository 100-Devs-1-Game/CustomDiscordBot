import os
from collections import defaultdict

import discord
from discord.ext import commands
from discord.ui import InputText, Modal

from databases import Database
from game import Game
from utils import Utils

CONTRIBUTION_TYPES = [
    "Programmer",
    "2D Artist",
    "3D Artist",
    "Composer",
    "Sound Designer",
    "Writer",
    "Voice Actor",
    "Translator",
]

PING_ROLES = {
    "Programmer": "PingCoder",
    "2D Artist": "Ping2DArtist",
    "3D Artist": "Ping3DArtist",
    "Composer": "PingComposer",
    "Sound Designer": "PingSFX",
    "Writer": "PingWriter",
    "Voice Actor": "PingVoice",
}

SUPPORTED_REQUEST_ROLES = [
    "Programmer",
    "2D Artist",
    "Composer",
    "Sound Designer",
    "Writer",
    "Voice Actor",
]

Utils.ensure_env_var(
    "CONTRIBUTORS_REQUEST_CHANNEL_ID", 1414479400250114058
)  # Test Server

CONTRIBUTOR_REQUEST_CHANNEL = int(os.getenv("CONTRIBUTORS_REQUEST_CHANNEL_ID", 0))


class Contributors(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    group = discord.SlashCommandGroup("contributors", "Contributor commands")

    @group.command(
        description="Register yourself (once) as a contributor on our Server"
    )
    async def register(self, ctx: discord.ApplicationContext):
        modal = ContributorRegisterModal(
            discord_username=str(ctx.author.name),
            discord_display_name=ctx.author.display_name,
        )
        await ctx.send_modal(modal)

    @group.command(description="Add a contributor to your game from your game channel")
    async def add(self, ctx: discord.ApplicationContext, member: discord.Member):
        game_info = (
            Database.get_default_game_info()
            if Utils.is_test_environment()
            else Database.get_game_info(ctx.channel.id)
        )
        if not game_info:
            await ctx.respond("⚠️ No game found for this channel.", ephemeral=True)
            return

        if ctx.author.name != game_info["owner"]:
            await ctx.respond(
                "❌ Only the game owner can add contributors.", ephemeral=True
            )
            return

        contributor = Database.fetch_one_as_dict(
            Database.GAMES_DB,
            "contributors",
            "discord_username = ?",
            (str(member.name),),
        )

        if not contributor:
            await ctx.channel.send(
                f"⚠️ {member.mention} please register as a contributor on our server ( `/contributors register` ) so you can be added.\nYou can react with ✅ to this message when you are done.",
            )

            # not registered — tell owner how to get them registered
            await ctx.respond(
                f"{member.display_name} is not registered as a contributor.",
                ephemeral=True,
            )
            return

        # show role dropdown
        await ctx.respond(
            f"Select contributors role for **member: {member.display_name}**:",
            view=ContributionRoleView(game_info, contributor["id"]),
            ephemeral=True,
        )

    @group.command(description="Export the list of contributors for the credits")
    async def export(self, ctx: discord.ApplicationContext):
        game_info = (
            Database.get_default_game_info()
            if Utils.is_test_environment()
            else Database.get_game_info(ctx.channel.id)
        )
        if not game_info:
            await ctx.respond("⚠️ No game found for this channel.", ephemeral=True)
            return

        owner_credit_name = Database.fetch_one_as_dict(
            Database.GAMES_DB,
            "contributors",
            "discord_username = ?",
            (game_info["owner"],),
        )

        if not owner_credit_name:
            await ctx.respond(
                "⚠️ Owner isn't registered as a contributor.", ephemeral=True
            )
            return

        contributors = Game.fetch_contributors(game_info, "credit_name")

        if not contributors:
            await ctx.respond("⚠️ No contributors found for this game.", ephemeral=True)
            return

        # Include owner at the top
        output_lines = ["Lead Game Designer"]
        output_lines.append(f"- {owner_credit_name['credit_name']}")
        output_lines.append("")  # Blank line after lead designer

        # Group contributors by role and sort alphabetically
        role_dict = defaultdict(list)
        for row in contributors:
            # row is a tuple like (credit_name, role)
            role_dict[row[1]].append(row[0])

        # Sort roles and contributors alphabetically
        for role in sorted(role_dict):
            output_lines.append(f"{role}")
            for name in sorted(role_dict[role]):
                output_lines.append(f"- {name}")
            output_lines.append("")  # Blank line between roles

        contributor_list = "\n".join(output_lines).strip()
        await ctx.respond(
            f"Contributors for **{game_info['name']}**:\n```markdown\n{contributor_list}\n```",
            ephemeral=True,
        )

    @group.command(description="Request a contributor in a specific role for your game")
    async def request(self, ctx: discord.ApplicationContext):
        game_info = (
            Database.get_default_game_info()
            if Utils.is_test_environment()
            else Database.get_game_info(ctx.channel.id)
        )
        if not game_info:
            await ctx.respond("⚠️ No game found for this channel.", ephemeral=True)
            return

        if ctx.author.name != game_info["owner"]:
            await ctx.respond(
                "❌ Only the game owner can request contributors.", ephemeral=True
            )
            return

        # show role dropdown
        await ctx.respond(
            "Request contributor role:",
            view=ContributionRoleView(game_info),
            ephemeral=True,
        )

    @group.command(description="View your contributor profile information")
    async def view(self, ctx: discord.ApplicationContext):
        contributor = Database.fetch_one_as_dict(
            Database.GAMES_DB,
            "contributors",
            "discord_username = ?",
            (str(ctx.author.name),),
        )

        if not contributor:
            await ctx.respond(
                "⚠️ You are not registered as a contributor. Use `/contributors register` first.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"Name: {contributor['credit_name']}",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="itch.io Link", value=contributor["itch_io_link"] or "", inline=False
        )
        embed.add_field(
            name="Alternative Link", value=contributor["alt_link"] or "", inline=False
        )

        await ctx.respond(embed=embed, ephemeral=True)

    @group.command(description="Update your credit name in your contributor profile")
    async def updatecreditname(self, ctx: discord.ApplicationContext, name: str):
        contributor = Database.fetch_one_as_dict(
            Database.GAMES_DB,
            "contributors",
            "discord_username = ?",
            (str(ctx.author.name),),
        )

        if not contributor:
            await ctx.respond(
                "⚠️ You are not registered as a contributor. Use `/contributors register` first.",
                ephemeral=True,
            )
            return

        Database.update_field(
            Database.GAMES_DB,
            "contributors",
            contributor["id"],
            "credit_name",
            name,
        )

        await ctx.respond("✅ Updated your credit name.", ephemeral=True)

    @group.command(description="Update your itch.io link in your contributor profile")
    async def updateitchiolink(self, ctx: discord.ApplicationContext, link: str):
        contributor = Database.fetch_one_as_dict(
            Database.GAMES_DB,
            "contributors",
            "discord_username = ?",
            (str(ctx.author.name),),
        )

        if not contributor:
            await ctx.respond(
                "⚠️ You are not registered as a contributor. Use `/contributors register` first.",
                ephemeral=True,
            )
            return

        Database.update_field(
            Database.GAMES_DB,
            "contributors",
            contributor["id"],
            "itch_io_link",
            link,
        )

        await ctx.respond("✅ Updated your itch.io link.", ephemeral=True)

    @group.command(
        description="Make user the admin of an itch.io page via an invite link"
    )
    async def makeitchioadmin(
        self, ctx: discord.ApplicationContext, user: discord.User, link: str
    ):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.respond("❌ You do not have permission to use this command.")
            return

        try:
            await user.send(
                f"Hello {user.display_name},\n\n"
                f"You have been made an admin for the itch.io page of a game.\n"
                f"Please follow the link to accept the invitation:\n{link}\n"
                "Make sure to check *Display as contributor* under *More->Admins* so this game shows up on your itch.io profile.\n\n"
                "\n\n**The Godot Collaborative Game Jam team**"
            )
        except discord.Forbidden:
            await ctx.respond(
                f"⚠️ Could not send DM to {user.display_name}. They might have DMs disabled.",
                ephemeral=True,
            )
            return

        await ctx.respond(f"✅ Invite sent to {user.display_name}")


class ContributorRegisterModal(Modal):
    def __init__(self, discord_username: str, discord_display_name: str | None):
        super().__init__(title="Register as Contributor")
        self.discord_username = discord_username
        self.discord_display_name = discord_display_name

        self.credit_name = InputText(
            label="Credit Name", placeholder="Name to display in credits", required=True
        )
        self.itch_io_link = InputText(
            label="itch.io Link",
            placeholder="Optional: https://yourgame.itch.io/",
            required=False,
        )
        self.alt_link = InputText(
            label="Alternative Link",
            placeholder="Optional: Portfolio, GitHub, etc.",
            required=False,
        )

        self.add_item(self.credit_name)
        self.add_item(self.itch_io_link)
        self.add_item(self.alt_link)

    async def callback(self, interaction: discord.Interaction):
        if Database.entry_exists(
            Database.GAMES_DB, "contributors", "discord_username", self.discord_username
        ):
            await interaction.response.send_message(
                "⚠️ You are already registered as a Contributor.", ephemeral=True
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
            ephemeral=True,
        )


class ContributionRoleSelect(discord.ui.Select):
    def __init__(self, game_info: dict, contributor_id: int):
        self.game_info = game_info
        self.contributor_id = contributor_id

        options = [
            discord.SelectOption(label=role, value=role) for role in CONTRIBUTION_TYPES
        ]
        super().__init__(
            placeholder="Select contribution type...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        chosen_role = self.values[0]

        if self.contributor_id == -1:
            # Requesting a contributor
            channel = interaction.guild.get_channel(self.CONTRIBUTOR_REQUEST_CHANNEL)
            if not channel:
                await interaction.response.send_message(
                    "⚠️ Contributor request channel not found. Please contact an admin.",
                    ephemeral=True,
                )
                return

            if chosen_role not in SUPPORTED_REQUEST_ROLES:
                await interaction.response.send_message(
                    f"⚠️ Role **{chosen_role}** cannot be requested at this time.",
                    ephemeral=True,
                )
                return

            channel_message = (
                f"**[{chosen_role}]** needed in <#{self.game_info['channel_id']}>"
            )

            # mention all users with the role
            role = PING_ROLES.get(chosen_role)
            if role:
                role_mention = discord.utils.get(interaction.guild.roles, name=role)
                channel_message += f"\n{role_mention.mention}"

            await channel.send(
                channel_message, allowed_mentions=discord.AllowedMentions(roles=True)
            )

            await interaction.response.send_message(
                f"✅ Requested contributor role: **{self.values[0]}**\n"
                "The request has been posted in <#{CONTRIBUTOR_REQUEST_CHANNEL}> you can mark it as done ✅ once you found someone.",
                ephemeral=True,
            )
            return

        # Insert link into relation table
        Database.insert_into_db(
            Database.GAMES_DB,
            "game_contributors",
            game_id=self.game_info["id"],
            contributor_id=self.contributor_id,
            role=chosen_role,
        )

        contributor = Database.fetch_one_as_dict(
            Database.GAMES_DB, "contributors", "id = ?", (self.contributor_id,)
        )

        await interaction.response.send_message(
            f"✅ Added contributor **{contributor['discord_display_name']}** with role: **{chosen_role}**",
            # ephemeral=True
        )


class ContributionRoleView(discord.ui.View):
    def __init__(self, game_info: dict, contributor_id: int = -1, timeout=60):
        super().__init__(timeout=timeout)
        self.add_item(ContributionRoleSelect(game_info, contributor_id))
