"""Active IJDS binary-geometry and comparator-frontier audit."""

from __future__ import annotations

from typing import Any

__all__ = ["load_v4_config", "solve_point_portfolio", "summarize_binary_geometry"]


def __getattr__(name: str) -> Any:
    """Preserve package-level conveniences without eager scientific imports."""
    if name == "load_v4_config":
        from src.ijds_audit.config import load_v4_config

        return load_v4_config
    if name == "summarize_binary_geometry":
        from src.ijds_audit.geometry import summarize_binary_geometry

        return summarize_binary_geometry
    if name == "solve_point_portfolio":
        from src.ijds_audit.portfolio import solve_point_portfolio

        return solve_point_portfolio
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
