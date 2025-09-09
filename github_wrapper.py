import os
from pathlib import Path

from dotenv import load_dotenv
from github import Auth, Github

load_dotenv()

# GitHub App credentials
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")  # GitHub App ID
PRIVATE_KEY_PATH = Path(
    "100devs-discord-bot.2025-08-26.private-key.pem"  # downloaded private key
)
GITHUB_INSTALLATION_ID = os.getenv(
    "GITHUB_INSTALLATION_ID"
)  # App installation ID for the repo/org

assert GITHUB_APP_ID
assert GITHUB_INSTALLATION_ID


class GithubWrapper:
    GITHUB_URL_PREFIX = "https://github.com/100-Devs-1-Game/"

    _instance = None

    @staticmethod
    def get_instance():
        if GithubWrapper._instance is None:
            GithubWrapper()
        return GithubWrapper._instance

    def __init__(self):
        if GithubWrapper._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            GithubWrapper._instance = self

            appauth = Auth.AppAuth(GITHUB_APP_ID, PRIVATE_KEY_PATH.read_text())
            installauth = appauth.get_installation_auth(int(GITHUB_INSTALLATION_ID))

            self.github = Github(auth=installauth)
            self.github_org = self.github.get_organization("100-Devs-1-Game")

    @staticmethod
    def get_github():
        return GithubWrapper.get_instance().github

    @staticmethod
    def get_github_org():
        return GithubWrapper.get_instance().github_org
