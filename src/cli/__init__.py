"""
AutoReiv CLI Module.
"""

__all__ = ["build_parser", "main"]


def __getattr__(name: str):
    if name in ("build_parser", "main"):
        from src.cli.main import build_parser, main

        return {"build_parser": build_parser, "main": main}[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
