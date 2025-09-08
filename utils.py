import os


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
