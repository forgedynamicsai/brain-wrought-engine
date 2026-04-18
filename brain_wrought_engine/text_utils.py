"""Shared text utilities used across the engine."""

from __future__ import annotations


def slug(name: str) -> str:
    """Convert an entity name to a safe filename stem."""
    return name.replace(" ", "_").replace("/", "-")
