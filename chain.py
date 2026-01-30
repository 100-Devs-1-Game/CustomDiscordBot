import discord
from discord.ext import commands
from datetime import datetime, timedelta

from utils import Utils

SCHEDULE_CHANNEL_ID = 1427878178155659437  # Channel ID for Chain Game Collab schedule
SCHEDULE_DAYS = 8  # Total number of days in the schedule
DATE_OFFSET = datetime(2026, 1, 31)  # Start date for the schedule (January 31, 2026)


class Chain(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    group = discord.SlashCommandGroup("chain", "Chain Game Collab commands")

    @group.command(
        description="Reserve a day in the Chain Game Collab"
    )
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

         # Push the edit
        await message.edit(content="\n".join(content))

        await ctx.respond("Schedule updated!", ephemeral=True)        

    @group.command(
        description="Update the schedule for the Chain Game Collab ( admin only )"
    )
    async def updateschedule(self, ctx: discord.ApplicationContext, day: int):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.respond("You do not have permission to use this command.", ephemeral=True)
            return

        await ctx.defer(ephemeral=True)

        schedule_channel = ctx.guild.get_channel(SCHEDULE_CHANNEL_ID)
        if schedule_channel is None:
            schedule_channel = await ctx.guild.fetch_channel(SCHEDULE_CHANNEL_ID)

        header_str = Chain.get_header_str()

        if await Utils.channel_is_empty(schedule_channel):
            await schedule_channel.send(header_str)

        # Get the very first message from the schedule channel
        async for msg in schedule_channel.history(limit=1, oldest_first=True):
            message = msg
            break

        content = message.content.splitlines()
        final_content = []
        # Ensure header exists
        if not content or not content[0].startswith(header_str):
            final_content = [header_str]
            for i in SCHEDULE_DAYS:
                timestamp = Chain.get_day_timestamp(i)
                final_content.append(f"**Day #{i} ({timestamp}):** Open")
        
        else:
            remove_day = True

            for line in content:
                if remove_day and line.startswith("**Day"):
                    remove_day = False
                    continue  # skip this line to remove the reservation
                final_content.append(line)

        # Push the edit
        await message.edit(content="\n".join(final_content))

        await ctx.respond("Schedule updated!", ephemeral=True)        


    @staticmethod
    def get_header_str() -> str:
        return "@silent**Reserved days:**"

    @staticmethod
    def get_day_timestamp(day: int) -> str:
        # Return a Discord timestamp string for a given day number with an 10:00 AM UTC time offset
        start_date = DATE_OFFSET
        day_date = start_date + timedelta(days=day - 1)
        return day_date.strftime("<t:%s:T>") % int(day_date.replace(hour=10, minute=0, second=0, microsecond=0).timestamp())