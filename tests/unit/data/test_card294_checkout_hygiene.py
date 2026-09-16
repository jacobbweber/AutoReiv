"""CARD-294: refuse live DBs/packs inside the git checkout; scratch is the only local temp zone."""


import pytest

from src.infrastructure.data.resolver import (
    ensure_live_data_root,
    is_checkout_live_tree_path,
    repo_root,
    resolve_agent_memory_path,
)


def test_checkout_root_is_forbidden_live_tree():
    root = repo_root()
    assert is_checkout_live_tree_path(root)
    assert is_checkout_live_tree_path(root / "packs" / "assistant")
    assert is_checkout_live_tree_path(root / "data")
    scratch = root / "scratch" / "tmp.db"
    assert not is_checkout_live_tree_path(scratch)


def test_ensure_live_data_root_refuses_checkout(tmp_path):
    with pytest.raises(ValueError, match="Refusing live data dir"):
        ensure_live_data_root(repo_root())
    with pytest.raises(ValueError, match="Refusing live data dir"):
        ensure_live_data_root(repo_root() / "data")
    # tmp outside checkout is fine
    ok = ensure_live_data_root(tmp_path)
    assert ok == tmp_path.resolve()


def test_resolve_agent_memory_path_refuses_checkout_data_dir():
    with pytest.raises(ValueError, match="Refusing live data dir"):
        resolve_agent_memory_path("assistant", data_dir=repo_root())


def test_resolve_agent_memory_path_allows_tmp(tmp_path):
    path = resolve_agent_memory_path("assistant", data_dir=tmp_path)
    assert path == tmp_path / "packs" / "assistant" / "assistant_memory.db"
    assert "Projects" not in str(path).replace("\\", "/") or "AppData" in str(path) or str(tmp_path) in str(path)


def test_scratch_gitkeep_exists():
    keep = repo_root() / "scratch" / ".gitkeep"
    assert keep.is_file()
