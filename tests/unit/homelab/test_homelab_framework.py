"""
Tests for Enterprise IT Homelab Documentation Framework and Template Library [CARD-198, REQ-FLEET-005].
"""

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
HOMELAB_DOCS_ROOT = REPO_ROOT / "notes" / "homelab"

EXPECTED_DIRECTORIES = [
    "00-governance",
    "10-network",
    "20-compute",
    "30-identity",
    "40-services",
    "50-runbooks",
    "templates",
]

EXPECTED_FILES = [
    "00-governance/sizing_tiers.md",
    "00-governance/naming_conventions.md",
    "10-network/vlan_matrix.md",
    "10-network/ipam_allocations.md",
    "10-network/dns_zones.md",
    "20-compute/hyperv_hosts.md",
    "20-compute/vm_catalog.md",
    "30-identity/active_directory.md",
    "40-services/port_matrix.md",
    "40-services/certificates.md",
    "50-runbooks/sop-provision-vm.md",
    "50-runbooks/sop-join-domain.md",
    "50-runbooks/sop-expand-disk.md",
    "templates/template-vlan-matrix.md",
    "templates/template-ipam-table.md",
    "templates/template-host-spec.md",
    "templates/template-sop-runbook.md",
]

VALID_DOC_TYPES = {
    "vlan_matrix",
    "ipam_table",
    "host_spec",
    "ad_plan",
    "port_matrix",
    "sop_runbook",
    "governance_spec",
    "service_catalog",
    "template",
}

VALID_OWNER_ROLES = {
    "homelab",
    "homelab-architect",
    "homelab-engineer",
    "homelab-admin",
    "homelab-janitor",
}

VALID_SCOPES = {
    "global",
    "network",
    "compute",
    "identity",
    "services",
    "governance",
    "operations",
}

VALID_STATUSES = {"active", "draft", "deprecated", "template"}

FRONTMATTER_PATTERN = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


def test_homelab_directories_exist():
    """Verify all standard enterprise IT homelab directories exist under notes/homelab/."""
    assert HOMELAB_DOCS_ROOT.is_dir(), f"Homelab documentation root missing: {HOMELAB_DOCS_ROOT}"
    for dir_name in EXPECTED_DIRECTORIES:
        d = HOMELAB_DOCS_ROOT / dir_name
        assert d.is_dir(), f"Expected directory missing: {d}"


def test_homelab_core_files_exist():
    """Verify all essential enterprise IT framework markdown files exist."""
    for rel_path in EXPECTED_FILES:
        f = HOMELAB_DOCS_ROOT / rel_path
        assert f.is_file(), f"Expected homelab documentation file missing: {f}"


def test_homelab_files_have_valid_frontmatter_schema():
    """Verify each markdown file contains valid YAML frontmatter adhering to CARD-198 schema."""
    for rel_path in EXPECTED_FILES:
        f = HOMELAB_DOCS_ROOT / rel_path
        if not f.is_file():
            pytest.fail(f"File missing for frontmatter test: {rel_path}")
        content = f.read_text(encoding="utf-8")
        match = FRONTMATTER_PATTERN.search(content)
        assert match is not None, f"Missing or invalid frontmatter delimiter in {rel_path}"

        raw_yaml = match.group(1)
        data = yaml.safe_load(raw_yaml)
        assert isinstance(data, dict), f"Frontmatter in {rel_path} must be a YAML mapping"

        # Check required fields
        for req_field in ("doc_type", "owner_role", "scope", "last_verified", "status"):
            assert req_field in data, f"Missing required frontmatter field '{req_field}' in {rel_path}"

        assert data["doc_type"] in VALID_DOC_TYPES, f"Invalid doc_type '{data['doc_type']}' in {rel_path}"
        assert data["owner_role"] in VALID_OWNER_ROLES, f"Invalid owner_role '{data['owner_role']}' in {rel_path}"
        assert data["scope"] in VALID_SCOPES, f"Invalid scope '{data['scope']}' in {rel_path}"
        assert data["status"] in VALID_STATUSES, f"Invalid status '{data['status']}' in {rel_path}"
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", str(data["last_verified"])), (
            f"last_verified must be YYYY-MM-DD date in {rel_path}"
        )
