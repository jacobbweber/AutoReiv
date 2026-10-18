"""Domain-level user-data root resolution and checkout boundary hooks [CARD-714].

Allows domain entities (WikiStore, CredentialVault) to resolve the active user-data
root and enforce checkout-hygiene guards without importing upward from src.infrastructure.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional, Union

LEGACY_WIKI_STRINGS = frozenset({"./data/wiki", "data/wiki", ".\\data\\wiki", "data\\wiki", ""})

_data_root_provider: Optional[Callable[[], Path]] = None
_wiki_path_provider: Optional[Callable[[], Path]] = None
_live_root_validator: Optional[Callable[[Union[str, Path]], Path]] = None


def configure_domain_data_hooks(
    *,
    data_root_provider: Callable[[], Path],
    wiki_path_provider: Callable[[], Path],
    live_root_validator: Callable[[Union[str, Path]], Path],
) -> None:
    """Register the infrastructure DataDirResolver callbacks for domain consumers."""
    global _data_root_provider, _wiki_path_provider, _live_root_validator
    _data_root_provider = data_root_provider
    _wiki_path_provider = wiki_path_provider
    _live_root_validator = live_root_validator


def _fallback_data_root() -> Path:
    env_data = os.environ.get("AUTOREIV_DATA_DIR")
    if env_data and str(env_data).strip():
        return Path(str(env_data).strip()).expanduser().resolve()
    if Path("/.dockerenv").exists():
        return Path("/data")
    if os.name == "nt":
        local_app = Path(os.environ["LOCALAPPDATA"]) if os.environ.get("LOCALAPPDATA") else (Path.home() / "AppData" / "Local")
        return (local_app / "AutoReiv").resolve()
    return (Path.home() / ".autoreiv").resolve()


def resolve_default_data_root() -> Path:
    """Return the active user-data root directory."""
    if _data_root_provider is not None:
        return Path(_data_root_provider())
    return _fallback_data_root()


def resolve_default_wiki_path() -> Path:
    """Return the active wiki vault directory."""
    if _wiki_path_provider is not None:
        return Path(_wiki_path_provider()).resolve()
    env_wiki = os.environ.get("AUTOREIV_WIKI_PATH")
    if env_wiki and str(env_wiki).strip() and str(env_wiki).strip() not in LEGACY_WIKI_STRINGS:
        return Path(str(env_wiki).strip()).expanduser().resolve()
    return (resolve_default_data_root() / "wiki").resolve()


def validate_live_data_root(data_dir: Union[str, Path]) -> Path:
    """Refuse live user-data roots that sit inside the git checkout outside scratch/."""
    if _live_root_validator is not None:
        return _live_root_validator(data_dir)
    root = Path(data_dir).expanduser().resolve()
    checkout = Path(__file__).resolve().parents[2]
    scratch = (checkout / "scratch").resolve()
    try:
        root.relative_to(checkout)
    except ValueError:
        return root
    try:
        root.relative_to(scratch)
        return root
    except ValueError as exc:
        raise ValueError(
            f"Refusing live data dir inside git checkout: {root}. "
            "Use AUTOREIV_DATA_DIR / platform user-data root, or write temp files under scratch/."
        ) from exc
