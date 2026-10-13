"""
DeepSeek. V4 models think before answering unless DEEPSEEK_THINKING=disabled.
"""
import os

from ..base import PROVIDERS, Provider

THINKING_MODES = ("", "enabled", "disabled")


@PROVIDERS.register("deepseek")
class DeepSeek(Provider):
    label = "DeepSeek"
    env_prefix = "DEEPSEEK"
    base_url = "https://api.deepseek.com"
    model = "deepseek-v4-flash"

    def __init__(self):
        super().__init__()
        self.thinking = os.getenv("DEEPSEEK_THINKING", "").strip().lower()
        if self.thinking not in THINKING_MODES:
            raise ValueError(f"DEEPSEEK_THINKING must be enabled or disabled, got {self.thinking!r}")

    @property
    def reasoning(self) -> bool:
        return self.thinking != "disabled"

    def request_options(self) -> dict:
        if not self.thinking:
            return {}
        return {"extra_body": {"thinking": {"type": self.thinking}}}
