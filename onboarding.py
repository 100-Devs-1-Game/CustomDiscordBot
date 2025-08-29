import discord
from discord.ext import commands

# === Configurable ===
GREETING_MESSAGE = "Welcome to our Community!"
COMMUNITY_DESCRIPTION = (
	"We are trying to make video games with as many contributors as possible. Will you help us?"
)
FOOTER_TEXT = (
"""
Type /help [...] or ask in one of the ❓ channels if you don't know where to start or need assistance. 
We are always happy to help!

Remember: Everyone is welcome to contribute, no matter your skill level or background.
If you don't think you have the required skills, we can help you learn them at least! 
Either way, you’re always welcome to suggest improvements to our projects, game features and workflow.
""" 
)

HIGHLIGHT_CHANNEL_IDS = [
	1393312261770051674,
	1394481813052850299,
	1393033401128194061
]

class Onboarding(commands.Cog):
	def __init__(self, bot: discord.Bot):
		self.bot = bot


	def build_onboarding_embed(self, guild: discord.Guild) -> discord.Embed:
		embed = discord.Embed(
			title=GREETING_MESSAGE,
			description=COMMUNITY_DESCRIPTION,
			color=discord.Color.green(),
		)
		
		channels_text = []
		for cid in HIGHLIGHT_CHANNEL_IDS:
			channel = guild.get_channel(cid)
			if channel:
				channels_text.append(f"👉 {channel.mention}")
		
		if channels_text:
			embed.add_field(
				name="Start by checking out:",
				value="\n".join(channels_text),
				inline=False,
			)

		embed.set_footer(text=FOOTER_TEXT.strip())
		return embed


	@commands.Cog.listener()
	async def on_member_join(self, member: discord.Member):
		embed = self.build_onboarding_embed(member.guild)
		try:
			await member.send(embed=embed)
		except discord.Forbidden:
			pass  # can't DM the user, ignore


	group = discord.SlashCommandGroup("onboarding", "Onboarding commands")

	@group.command(name="test")
	async def test(self, ctx: discord.ApplicationContext):
		"""Test the onboarding message."""
		embed = self.build_onboarding_embed(ctx.guild)
		await ctx.respond(embed=embed, ephemeral=True)