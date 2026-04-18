"""Tests for brain_wrought_engine.ingestion.setup_friction."""
from __future__ import annotations

from brain_wrought_engine.ingestion.setup_friction import SetupBlock, score_setup_friction


def test_zero_friction() -> None:
    """Empty setup lists → score 1.0."""
    setup = SetupBlock()
    assert score_setup_friction(setup) == 1.0


def test_max_friction_exact() -> None:
    """Exactly 20 combined actions → score 0.0."""
    setup = SetupBlock(
        commands=["cmd"] * 10,
        prompts=["prompt"] * 5,
        config_files=["file"] * 5,
    )
    assert score_setup_friction(setup) == 0.0


def test_beyond_max_clamped() -> None:
    """More than 20 actions → clamped to 0.0, not negative."""
    setup = SetupBlock(
        commands=["cmd"] * 30,
        prompts=["prompt"] * 20,
    )
    assert score_setup_friction(setup) == 0.0


def test_auto_detected_does_not_penalize() -> None:
    """auto_detected entries are free — they do not reduce the score."""
    setup_with = SetupBlock(auto_detected=["api_key", "vault_path", "llm_model"] * 10)
    setup_without = SetupBlock()
    assert score_setup_friction(setup_with) == score_setup_friction(setup_without) == 1.0


def test_real_example_good() -> None:
    """A 'good' system: 1 command, 0 prompts, 0 config files → ~0.95."""
    setup = SetupBlock(commands=["pip install brain-wrought-submission"])
    score = score_setup_friction(setup)
    assert abs(score - 0.95) < 1e-9


def test_real_example_typical() -> None:
    """A 'typical' system: 3 commands, 2 prompts, 1 config → ~0.70."""
    setup = SetupBlock(
        commands=["git clone ...", "pip install -r requirements.txt", "python setup.py"],
        prompts=["Enter API key:", "Select vault path:"],
        config_files=["config.yaml"],
    )
    score = score_setup_friction(setup)
    assert abs(score - 0.70) < 1e-9


def test_real_example_painful() -> None:
    """A 'painful' system: 8 commands + 6 prompts + 3 config files → 0.15."""
    setup = SetupBlock(
        commands=["cmd"] * 8,
        prompts=["prompt"] * 6,
        config_files=["file"] * 3,
    )
    score = score_setup_friction(setup)
    assert abs(score - 0.15) < 1e-9


def test_score_in_unit_interval() -> None:
    """Score is always in [0.0, 1.0] regardless of input."""
    for n in range(0, 50, 5):
        setup = SetupBlock(commands=["x"] * n)
        s = score_setup_friction(setup)
        assert 0.0 <= s <= 1.0


def test_idempotent() -> None:
    """Calling score_setup_friction twice with the same input returns the same result."""
    setup = SetupBlock(commands=["a", "b"], prompts=["c"])
    assert score_setup_friction(setup) == score_setup_friction(setup)
