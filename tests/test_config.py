import pytest

from maintenance_agent.config import ConfigError, Settings


def test_from_env_loads_required_vars(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-test")
    monkeypatch.delenv("MAINTENANCE_AGENT_MODEL", raising=False)
    monkeypatch.delenv("MAINTENANCE_AGENT_MAX_TURNS", raising=False)
    monkeypatch.delenv("MAINTENANCE_AGENT_MAX_COST_USD", raising=False)

    settings = Settings.from_env()

    assert settings.anthropic_api_key == "sk-ant-test"
    assert settings.github_token == "ghp-test"
    assert settings.model == "claude-sonnet-5"
    assert settings.max_turns == 20
    assert settings.max_cost_per_run_usd == 1.0


def test_from_env_missing_required_vars_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        Settings.from_env()


def test_from_env_missing_github_token_only(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(ConfigError, match="GITHUB_TOKEN"):
        Settings.from_env()


def test_from_env_respects_overrides(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-test")
    monkeypatch.setenv("MAINTENANCE_AGENT_MODEL", "claude-opus-5")
    monkeypatch.setenv("MAINTENANCE_AGENT_MAX_TURNS", "5")
    monkeypatch.setenv("MAINTENANCE_AGENT_MAX_COST_USD", "0.25")

    settings = Settings.from_env()

    assert settings.model == "claude-opus-5"
    assert settings.max_turns == 5
    assert settings.max_cost_per_run_usd == 0.25


def test_from_env_invalid_max_turns_raises(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-test")
    monkeypatch.setenv("MAINTENANCE_AGENT_MAX_TURNS", "not-a-number")

    with pytest.raises(ConfigError, match="Invalid configuration"):
        Settings.from_env()
