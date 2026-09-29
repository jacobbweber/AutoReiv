"""Copy-if-missing bundled user skill packs into $DATA_DIR/skills [REQ-BUILD-015].

CARD-118: okta-admin is not a product seed. CARD-569: the pack builder seed is removed.
CARD-497 D10: a seed the operator never edited (its hash matches a shipped version) is refreshed.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path
from typing import Iterable, Union

logger = logging.getLogger(__name__)

RETIRED_OKTA_ADMIN_PACK_ID = "okta-admin"
BUNDLED_PACK_IDS: tuple[str, ...] = (
    "proposals",
    "wiki",
    "sandbox",
    "coordination",
    "worker",
    "education-priming",
    "education-dual-coding",
    "education-construction",
    "education-application",
    "sqlite-storage",
)


# sha256 of the LF-normalized SKILL.md for every version we shipped. A dest whose hash is in this
# set was never edited, so it may be replaced with the current seed [CARD-497 D10].
SHIPPED_SEED_SHA256: dict[str, frozenset[str]] = {}


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


def _normalized_sha256(path: Path) -> str:
    text = path.read_bytes().decode("utf-8", errors="replace").replace("\r\n", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _refresh_if_unedited(source: Path, dest: Path, pack_id: str) -> bool:
    """Replace ``dest`` with ``source`` only when ``dest`` is byte-for-byte an older shipped seed."""
    shipped = SHIPPED_SEED_SHA256.get(pack_id)
    if not shipped or not dest.is_file() or not source.is_file():
        return False
    current = _normalized_sha256(dest)
    if current == _normalized_sha256(source):
        return False
    if current not in shipped:
        logger.info("Bundled skill %s at %s was edited by the operator; not refreshing it", pack_id, dest)
        return False
    tmp = dest.with_name(dest.name + ".seeding")
    try:
        shutil.copy2(source, tmp)
        tmp.replace(dest)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    logger.info("Refreshed unedited bundled skill %s -> %s", pack_id, dest)
    return True


def seed_bundled_skill_packs(skills_path: Union[str, Path], pack_ids: Iterable[str] | None = None) -> None:
    """Copy bundled SKILL.md files into ``skills_path`` when dest is missing.

    Never overwrites an edited dest (user edits stay); an unedited older shipped seed is refreshed
    [CARD-497 D10]. Default pack list is AutoReiv's pack-build runbook.
    """
    root = Path(skills_path)
    root.mkdir(parents=True, exist_ok=True)

    legacy_recommend = root / "recommend-capability"
    if legacy_recommend.is_dir():
        try:
            shutil.rmtree(legacy_recommend)
            logger.info("Cleaned up legacy recommend-capability skill pack at %s", legacy_recommend)
        except OSError:
            pass

    ids = tuple(pack_ids) if pack_ids is not None else BUNDLED_PACK_IDS
    for pack_id in ids:
        source = bundled_skill_md(pack_id)
        dest = root / pack_id / "SKILL.md"
        if not _copy_if_missing(source, dest, pack_id):
            _refresh_if_unedited(source, dest, pack_id)
