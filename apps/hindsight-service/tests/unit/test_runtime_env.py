import pytest

from core.utils.runtime import dev_mode_active


def test_dev_mode_active_false_when_disabled(monkeypatch):
    monkeypatch.delenv("DEV_MODE", raising=False)
    assert dev_mode_active() is False


def test_dev_mode_active_true_for_localhost(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:3000")
    assert dev_mode_active() is True


def test_dev_mode_active_raises_for_remote_host(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("APP_BASE_URL", "https://app-staging.hindsight-ai.com")
    with pytest.raises(RuntimeError):
        dev_mode_active()


def test_dev_mode_active_without_app_base_requires_allow(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.delenv("APP_BASE_URL", raising=False)
    monkeypatch.delenv("ALLOW_DEV_MODE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    with pytest.raises(RuntimeError):
        dev_mode_active()

    monkeypatch.setenv("ALLOW_DEV_MODE", "true")
    assert dev_mode_active() is True
