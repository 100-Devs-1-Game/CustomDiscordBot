import os
from datetime import datetime, timedelta, timezone

import discord


class Utils:
    @staticmethod
    def is_test_environment() -> bool:
        return os.getenv("IS_TEST", "false").lower() == "true"

    @staticmethod
    async def send_guide_link(channel, user):
        await channel.send(
            f"{user.mention} Here is the link to our 📕 Guide: "
            "<https://docs.google.com/document/d/1BL1erhDZDM8XW_X2w3OuT16gAEbvKB8ZxjXn0cByAJ4/edit?usp=drive_link>"
        )

    # Remove all messages from channels that contain links to the games channel
    @staticmethod
    async def purge_messages_with_game_channel_link(
        guild, channel_ids, game_channel_id
    ):
        for channel_id in channel_ids:
            channel = guild.get_channel(channel_id)
            if channel is None:
                continue

            content_str = f"{game_channel_id}"

            for message in await channel.history(limit=100).flatten():
                if content_str in message.content:
                    await message.delete()
                    print(
                        f"Deleted message {message.id}: {message.content} in channel {channel.id}"
                    )

    @staticmethod
    def ensure_env_var(key: str, value: str, filename: str = ".env"):
        try:
            with open(filename, "r") as f:
                content = f.read()
        except FileNotFoundError:
            content = ""

        # check if key exists already
        for line in content.splitlines():
            if line.strip().startswith(f"{key}="):
                return  # already exists, do nothing

        # make sure file ends with a newline before appending
        with open(filename, "a") as f:
            if content and not content.endswith("\n"):
                f.write("\n")
            f.write(f"{key}={value}\n")

    @staticmethod
    def build_timestamp(days_from_now: int) -> str:
        target = datetime.now(timezone.utc) + timedelta(days=days_from_now)
        return f"<t:{int(target.timestamp())}:R>"  # :R = relative (e.g. "in 2 days")

    @staticmethod
    async def channel_is_empty(channel: discord.TextChannel) -> bool:
        async for _ in channel.history(limit=1):
            return False  # found at least one message
        return True
