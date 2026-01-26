import discord
from discord.ext import commands

from onboarding import Onboarding

COMMANDS = [
    "/help ...",
    # "/assets listaccepted",
    # "/assets listrequests",
    # "/assets request",
    "/contributors add",
    "/contributors export",
    "/contributors register",
    "/contributors request",
    "/contributors updatecreditname",
    "/contributors updateitchiolink",
    "/contributors updatetimezone",
    "/contributors trustlevel",
    "/contributors timezone",
    "/create_game",
    "/fun",
    "/game info",
    "/game setdescription",
    "/game requestitchio",
    # "/game setitchiolink",
    # "/contributors makeitchioadmin",
    "/game build",
    "/game test",
    "/game updatereleasedate",
    "/onboarding test",
]


class Help(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    group = discord.SlashCommandGroup("help", "Help commands")

    @group.command(description="Overview of the Discord server")
    async def overview(self, ctx: discord.ApplicationContext):
        await ctx.respond(
            embed=Onboarding.build_onboarding_embed(ctx.guild), ephemeral=True
        )

    @group.command(description="Show information about the current channel")
    async def channel(self, ctx: discord.ApplicationContext):
        if isinstance(ctx.channel, discord.TextChannel):
            desc = ctx.channel.topic or "No description set for this channel."
            embed = discord.Embed(
                title=f"#{ctx.channel.name}",
                description=desc,
                color=discord.Color.blue(),
            )
        else:
            embed = discord.Embed(
                title="DM Channel",
                description="Direct messages don't have a channel description.",
                color=discord.Color.red(),
            )
        await ctx.respond(embed=embed, ephemeral=True)

    @group.command(description="How to access our GitHub organization")
    async def github(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title="Github Access",
            description="You need to request an invite to our GitHub organization here <#1395558585173409882>",
            url="https://github.com/orgs/100-Devs-1-Game",
        )
        await ctx.respond(embed=embed, ephemeral=True)

    @group.command(description="Link to our guide for the 100 Games challenge")
    async def guide(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title="100 Games in 100 Days Guide",
            url="https://docs.google.com/document/d/1BL1erhDZDM8XW_X2w3OuT16gAEbvKB8ZxjXn0cByAJ4/edit?usp=drive_link",
        )
        await ctx.respond(embed=embed, ephemeral=True)

    @group.command(description="List all bot commands")
    async def commandlist(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title="Bot Commands",
            description="Here is a list of available bot commands:\n"
            "they all have their individual help texts",
            color=discord.Color.purple(),
        )

        embed.add_field(name="Commands", value="\n".join(COMMANDS), inline=False)
        await ctx.respond(embed=embed, ephemeral=True)
