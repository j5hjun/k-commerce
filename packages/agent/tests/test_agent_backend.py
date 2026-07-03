import asyncio

import pytest

from k_commerce_agent.agent import ModelNotConfiguredError, build_agent
from k_commerce_agent.config import Settings


def test_settings_default_mcp_launch_targets_mcp_module() -> None:
    settings = Settings()
    assert settings.mcp_args == ["-m", "k_commerce_mcp.server"]
    assert settings.mcp_server_name == "k-commerce"


def test_build_agent_without_model_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from k_commerce_agent import agent as agent_module

    monkeypatch.setattr(agent_module.settings, "llm_model", "")
    with pytest.raises(ModelNotConfiguredError):
        asyncio.run(build_agent())
