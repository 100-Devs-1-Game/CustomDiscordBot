from datetime import datetime, timedelta

import discord
from discord.ext import commands

from utils import Utils

SCHEDULE_CHANNEL_ID = 1466537129583706305  # Channel ID for Chain Game Collab schedule
SCHEDULE_DAYS = 8  # Total number of days in the schedule
DATE_OFFSET = datetime(2026, 1, 31)  # Start date for the schedule (January 31, 2026)


class Chain(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    group = discord.SlashCommandGroup("chain", "Chain Game Collab commands")

    @group.command(description="Reserve a day in the Chain Game Collab")
    async def claim(self, ctx: discord.ApplicationContext, day: int):
        await ctx.defer(ephemeral=True)

        schedule_channel = ctx.guild.get_channel(SCHEDULE_CHANNEL_ID)
        if schedule_channel is None:
            schedule_channel = await ctx.guild.fetch_channel(SCHEDULE_CHANNEL_ID)

        # Get the very first message from the schedule channel
        async for msg in schedule_channel.history(limit=1, oldest_first=True):
            message = msg
            break

        content = message.content.splitlines()
        final_content = []
        day_found = False
        for line in content:
            if line.startswith(f"*Day #{day}"):
                day_found = True
                if "Open" in line:
                    reserver_name = ctx.author.mention
                    final_content.append(
                        Chain.get_day_str(day) + f"Reserved by {reserver_name}"
                    )
                else:
                    await ctx.respond(
                        f"Day #{day} is already reserved.", ephemeral=True
                    )
                    return
            else:
                final_content.append(line)

        if not day_found:
            await ctx.respond(f"Day #{day} not found in the schedule.", ephemeral=True)
            return

        # Push the edit
        await message.edit(content="\n".join(final_content))

        await ctx.respond("Schedule updated!", ephemeral=True)

    @group.command(
        description="Update the schedule for the Chain Game Collab ( admin only )"
    )
    async def updateschedule(self, ctx: discord.ApplicationContext):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.respond(
                "You do not have permission to use this command.", ephemeral=True
            )
            return

        await ctx.defer(ephemeral=True)

        schedule_channel = ctx.guild.get_channel(SCHEDULE_CHANNEL_ID)
        if schedule_channel is None:
            schedule_channel = await ctx.guild.fetch_channel(SCHEDULE_CHANNEL_ID)

        header_str = Chain.get_header_str()

        empty = False
        if await Utils.channel_is_empty(schedule_channel):
            empty = True
            await schedule_channel.send(header_str)

        # Get the very first message from the schedule channel
        async for msg in schedule_channel.history(limit=1, oldest_first=True):
            message = msg
            break

        content = message.content.splitlines()
        final_content = []
        if empty:
            final_content = [header_str]
            for i in range(1, SCHEDULE_DAYS + 1):
                final_content.append(Chain.get_day_str(i) + "Open")

        else:
            first_day = True
            last_day_index = 0
            add_day = False

            for line in content:
                if line.startswith("*Day"):
                    if first_day:
                        first_day = False
                        timestamp_str = line.split(":")[1]
                        date = datetime.fromtimestamp(int(timestamp_str))
                        print("First day date:", date.isoformat())

                        if date < datetime.now() - timedelta(days=1):
                            add_day = True
                            continue  # skip this line to remove the reservation
                    last_day_index = line.split("#")[1].split("*")[0]
                final_content.append(line)
            if add_day:
                final_content.append(
                    Chain.get_day_str(int(last_day_index) + 1) + "Open"
                )

        # Push the edit
        await message.edit(content="\n".join(final_content))

        await ctx.respond("Schedule updated!", ephemeral=True)

    @staticmethod
    def get_header_str() -> str:
        return "**Reserved days:**\n"

    @staticmethod
    def get_day_timestamp(day: int) -> str:
        # Return a Discord timestamp string for a given day number with an 10:00 AM UTC time offset
        start_date = DATE_OFFSET
        day_date = start_date + timedelta(days=day - 1)
        return "<t:%s:d>" % int(
            day_date.replace(hour=10, minute=0, second=0, microsecond=0).timestamp()
        )

    @staticmethod
    def get_day_str(day: int) -> str:
        return f"*Day #{day}* ({Chain.get_day_timestamp(day)}): "
