"""Copy-if-missing bundled user skill packs into $DATA_DIR/skills [REQ-BUILD-015].

CARD-118: okta-admin is not a product seed. CARD-119 ships build-agent-pack and recommend-capability for AutoReiv.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Iterable, Union

logger = logging.getLogger(__name__)

RETIRED_OKTA_ADMIN_PACK_ID = "okta-admin"
BUNDLED_PACK_IDS: tuple[str, ...] = ("build-agent-pack", "recommend-capability", "wiki")


def bundled_seed_root() -> Path:
    """Repo seed directory next to this module (src/infrastructure/skills/seeds)."""
    return Path(__file__).resolve().parent / "seeds"


def bundled_skill_md(pack_id: str) -> Path:
    """Path to the bundled SKILL.md for a pack id."""
    return bundled_seed_root() / pack_id / "SKILL.md"



def _copy_if_missing(source: Path, dest: Path, pack_id: str) -> bool:
    if dest.exists():
        return False
    if not source.is_file():
        logger.warning("Bundled skill pack %s missing at %s; skip seed", pack_id, source)
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".seeding")
    try:
        if tmp.exists():
            tmp.unlink()
        shutil.copy2(source, tmp)
        tmp.replace(dest)
        logger.info("Seeded bundled skill pack %s -> %s", pack_id, dest)
        return True
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def seed_bundled_skill_packs(skills_path: Union[str, Path], pack_ids: Iterable[str] | None = None) -> None:
    """Copy bundled SKILL.md files into ``skills_path`` when dest is missing.

    Never overwrites an existing dest (user edits stay). Default pack list is AutoReiv's pack-build runbook.
    """
    root = Path(skills_path)
    root.mkdir(parents=True, exist_ok=True)
    ids = tuple(pack_ids) if pack_ids is not None else BUNDLED_PACK_IDS
    for pack_id in ids:
        _copy_if_missing(bundled_skill_md(pack_id), root / pack_id / "SKILL.md", pack_id)
