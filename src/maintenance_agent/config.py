"""Runtime configuration, loaded from environment variables.

Kept as a plain Pydantic model with an explicit from_env() constructor
rather than pulling in pydantic-settings, per the project's
"avoid unnecessary dependencies" principle.
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


class Settings(BaseModel):
    anthropic_api_key: str
    github_token: str

    model: str = "claude-sonnet-5"
    max_turns: int = Field(default=20, gt=0)
    max_cost_per_run_usd: float = Field(default=1.0, gt=0)

    @classmethod
    def from_env(cls) -> "Settings":
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        github_token = os.environ.get("GITHUB_TOKEN")

        missing = [
            name
            for name, value in (
                ("ANTHROPIC_API_KEY", anthropic_api_key),
                ("GITHUB_TOKEN", github_token),
            )
            if not value
        ]
        if missing:
            raise ConfigError(
                "Missing required environment variable(s): "
                f"{', '.join(missing)}. See .env.example."
            )

        kwargs: dict[str, str] = {
            "anthropic_api_key": anthropic_api_key,
            "github_token": github_token,
        }
        if model := os.environ.get("MAINTENANCE_AGENT_MODEL"):
            kwargs["model"] = model
        if max_turns := os.environ.get("MAINTENANCE_AGENT_MAX_TURNS"):
            kwargs["max_turns"] = max_turns
        if max_cost := os.environ.get("MAINTENANCE_AGENT_MAX_COST_USD"):
            kwargs["max_cost_per_run_usd"] = max_cost

        try:
            return cls(**kwargs)
        except Exception as exc:  # pydantic ValidationError, invalid ints/floats, etc.
            raise ConfigError(f"Invalid configuration: {exc}") from exc
