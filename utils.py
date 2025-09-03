import os


class Utils:
	@staticmethod
	def is_test_environment() -> bool:
		return os.getenv("IS_TEST", "false").lower() == "true"
