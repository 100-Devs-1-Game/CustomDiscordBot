import os
from collections import defaultdict
from enum import IntEnum

import discord
from discord.ext import commands
from discord.ui import InputText, Modal

from databases import Database
from game import Game, GameState
from utils import Utils


class TrustLevel(IntEnum):
    UNKNOWN = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4


CONTRIBUTION_TYPES = [
    "Programmer",
    "2D Artist",
    "3D Artist",
    "Composer",
    "Sound Designer",
    "Writer",
    "Voice Actor",
    "Translator",
    "QA",
    "UI/UX Designer",
    "Game Designer",
]

PING_ROLES = {
    "Programmer": "PingCoder",
    "2D Artist": "Ping2DArtist",
    "3D Artist": "Ping3DArtist",
    "Composer": "PingComposer",
    "Sound Designer": "PingSFX",
    "Writer": "PingWriter",
    "Voice Actor": "PingVoice",
    "UI/UX Designer": "PingUI",
    "Game Designer": "PingDesigner",
}

SUPPORTED_REQUEST_ROLES = [
    "Programmer",
    "2D Artist",
    "3D Artist",
    "Composer",
    "Sound Designer",
    "Writer",
    "Voice Actor",
    "UI/UX Designer",
    "Game Designer",
]

TRUST_REWARD_ROLES = ["Original100"]

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

        if (
            ctx.author.name != game_info["owner"]
            and not ctx.author.guild_permissions.manage_guild
        ):
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
                f"⚠️ {member.mention} please register as a contributor on our server ( type `/contributors register` in the chat and press return ) so you can be added.\nYou can react with ✅ to this message when you are done.",
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

    @group.command(description="Remove a contributor from this game")
    async def remove(self, ctx: discord.ApplicationContext, user_name: str):
        game_info = (
            Database.get_default_game_info()
            if Utils.is_test_environment()
            else Database.get_game_info(ctx.channel.id)
        )
        if not game_info:
            await ctx.respond("⚠️ No game found for this channel.", ephemeral=True)
            return

        if not ctx.author.guild_permissions.manage_guild:
            await ctx.respond(
                "❌ Only an admin can remove contributors.", ephemeral=True
            )
            return

        contributor = Database.fetch_one_as_dict(
            Database.GAMES_DB,
            "contributors",
            "discord_username = ?",
            (str(user_name),),
        )

        if not contributor:
            await ctx.respond(
                f"⚠️ {user_name} is not registered as a contributor.",
                ephemeral=True,
            )
            return

        # Remove contributor from game_contributors table
        Database.delete_from_db(
            Database.GAMES_DB,
            "game_contributors",
            "game_id = ? AND contributor_id = ?",
            (str(game_info["id"]), str(contributor["id"])),
        )

        await ctx.respond(
            f"✅ Removed contributor **{user_name}** from the game.",
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

        if (
            ctx.author.name != game_info["owner"]
            and not ctx.author.guild_permissions.manage_guild
        ):
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

        if not link.startswith("https://") and not link.startswith("http://"):
            link = "https://" + link

        Database.update_field(
            Database.GAMES_DB,
            "contributors",
            contributor["id"],
            "itch_io_link",
            link,
        )

        await ctx.respond("✅ Updated your itch.io link.", ephemeral=True)

    @group.command(description="Update the time zone in your contributor profile")
    async def updatetimezone(self, ctx: discord.ApplicationContext, time_zone: int):
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
            "time_zone",
            time_zone,
        )

        if time_zone >= 0:
            time_zone_str = f"+{time_zone}"
        else:
            time_zone_str = str(time_zone)
        await ctx.respond(
            f"✅ Updated your time zone to UTC {time_zone_str}.", ephemeral=True
        )

    @group.command(
        description="Make user the admin of an itch.io page via an invite link"
    )
    async def makeitchioadmin(
        self, ctx: discord.ApplicationContext, user: discord.User, link: str
    ):
        # if not ctx.author.guild_permissions.manage_guild:
        #     await ctx.respond("❌ You do not have permission to use this command.")
        #     return

        try:
            await user.send(
                f"Hello {user.display_name},\n\n"
                f"You have been made an admin for the itch.io page of a game by {ctx.author.display_name}.\n"
                f"Please follow the link to accept the invitation:\n{link}\n"
                "Make sure to check *Display as contributor* under *Edit Game->More->Admins* so this game shows up in your itch.io profile.\n\n"
                "\n\n**The Godot Collaborative Game Jam team**"
            )
        except discord.Forbidden:
            await ctx.respond(
                f"⚠️ Could not send DM to {user.display_name}. They might have DMs disabled.",
                ephemeral=True,
            )
            return

        await ctx.respond(f"✅ Invite sent to {user.display_name}")

    @group.command(description="Check the estimated trust level of a user")
    async def trustlevel(self, ctx: discord.ApplicationContext, user: discord.User):
        trust_level = Contributors.calculate_trust(user)
        await ctx.respond(
            f"✅ {user.display_name}'s estimated trust level is: **{TrustLevel(trust_level).name.replace('_', ' ').title()}**",
            ephemeral=True,
        )

    @group.command(description="Set trust points for a contributor ( admin only )")
    async def settrustpoints(
        self,
        ctx: discord.ApplicationContext,
        user: discord.User,
        points: int,
        remarks: str = "",
    ):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.respond("❌ You do not have permission to use this command.")
            return

        contributor = Database.fetch_one_as_dict(
            Database.GAMES_DB,
            "contributors",
            "discord_username = ?",
            (str(user.name),),
        )
        if not contributor:
            await ctx.respond(
                "⚠️ This user is not registered as a contributor.",
                ephemeral=True,
            )
            return

        Database.update_field(
            Database.GAMES_DB,
            "contributors",
            contributor["id"],
            "trust_points",
            points,
        )

        Database.update_field(
            Database.GAMES_DB,
            "contributors",
            contributor["id"],
            "trust_remarks",
            remarks,
        )
        await ctx.respond(
            f"✅ {user.display_name}'s Trust Points have been set to {points}.",
            ephemeral=True,
        )

    @group.command(description="View trust points for a contributor ( admin only )")
    async def viewtrustpoints(
        self, ctx: discord.ApplicationContext, user: discord.User
    ):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.respond("❌ You do not have permission to use this command.")
            return

        contributor = Database.fetch_one_as_dict(
            Database.GAMES_DB,
            "contributors",
            "discord_username = ?",
            (str(user.name),),
        )
        if not contributor:
            await ctx.respond(
                "⚠️ This user is not registered as a contributor.",
                ephemeral=True,
            )
            return

        trust_points = contributor.get("trust_points", 0)
        trust_remarks = contributor.get("trust_remarks", "")
        await ctx.respond(
            f"✅ {user.display_name}'s Trust Points: {trust_points}\n"
            f"Remarks: {trust_remarks}",
            ephemeral=True,
        )

    @group.command(description="View list of all trust points ( admin only )")
    async def viewalltrustpoints(self, ctx: discord.ApplicationContext):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.respond("❌ You do not have permission to use this command.")
            return

        await ctx.defer(ephemeral=True)

        # fetch all contributors with trust points != 0
        contributors = Database.fetch_all_as_dict_arr(
            Database.GAMES_DB,
            "contributors",
            "trust_points != 0",
            (),
        )
        if not contributors:
            # use follow up to send message after defer
            await ctx.followup.send(
                "⚠️ No contributors found.",
                ephemeral=True,
            )
            return

        response = "✅ List of all Trust Points:\n"
        for contributor in contributors:
            # user = await ctx.bot.fetch_user(contributor["discord_username"])
            trust_points = contributor.get("trust_points", 0)
            trust_remarks = contributor.get("trust_remarks", "")
            member = ctx.guild.get_member_named(contributor["discord_username"])
            if member:
                display_name = (
                    member.display_name
                )  # Server nickname or global display name
            else:
                display_name = f"{contributor['discord_username']} (left)"
            response += (
                f"**{display_name}**:  {trust_points} points , *{trust_remarks}*\n"
            )

        # use follow up to send message after defer
        await ctx.followup.send(response, ephemeral=True)

    @staticmethod
    def calculate_trust(user: discord.User) -> int:
        print(f"Calculating trust for user: {user.name}")

        # admins have maximum trust
        if user.guild_permissions.administrator:
            print("User is admin, setting trust to VERY_HIGH")
            return TrustLevel.VERY_HIGH.value

        trust_score = 0

        user_role_names = [role.name for role in user.roles]

        # +1 for each TRUST_REWARD_ROLES role
        for role_name in TRUST_REWARD_ROLES:
            if role_name in user_role_names:
                trust_score += 1

        print(f"Trust score after roles: {trust_score}")

        # fetch all released games this user has contributed to
        contributor = Database.fetch_one_as_dict(
            Database.GAMES_DB, "contributors", "discord_username = ?", (str(user.name),)
        )
        if not contributor:
            return 0

        # +1 for each released or KEEP_DEVELOPING game contributed to
        contributed_games = Database.fetch_all_as_dict_arr(
            Database.GAMES_DB,
            "game_contributors gc JOIN games g ON gc.game_id = g.id",
            "gc.contributor_id = ? AND g.state IN (?, ?)",
            (
                str(contributor["id"]),
                GameState.RELEASED.value,
                GameState.KEEP_DEVELOPING.value,
            ),
        )
        trust_score += len(contributed_games)

        print(f"Trust score after contributed games: {trust_score}")

        unknown = trust_score == 0
        trust_score = min(trust_score, 2)

        # add contributor trust points from the database
        trust_points = contributor.get("trust_points", 0)
        trust_score += trust_points

        print(f"Trust score after trust points: {trust_score}")

        if not unknown:
            trust_score += 2  # start from medium if we have any trust points

        if not unknown or trust_score < 0:
            trust_score = max(trust_score, TrustLevel.LOW.value)

        trust_score = min(trust_score, TrustLevel.VERY_HIGH.value)
        print(f"Final trust score: {trust_score}")

        return trust_score


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
        self.time_zone = InputText(
            label="Time Zone ( UTC Offset )",
            placeholder="-12 to +12",
            max_length=3,
            required=True,
        )

        self.add_item(self.credit_name)
        self.add_item(self.itch_io_link)
        self.add_item(self.alt_link)
        self.add_item(self.time_zone)

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
            time_zone=self.time_zone.value,
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
            channel = interaction.guild.get_channel(CONTRIBUTOR_REQUEST_CHANNEL)
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

            # create a channel thread from that last posted message
            last_message = await channel.history(limit=1).flatten()
            if last_message:
                thread = await last_message[0].create_thread(name="Details")

                await thread.send("Post more details about your request here:")

            await interaction.response.send_message(
                f"✅ Requested contributor role: **{self.values[0]}**\n"
                f"The request has been posted in <#{CONTRIBUTOR_REQUEST_CHANNEL}> you can mark it as done ✅ once you found someone."
                "\nA thread has been created in that channel as well for you to post more details about your request.",
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
