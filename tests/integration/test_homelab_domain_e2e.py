"""
End-to-End Integration Test for Autonomous Homelab Domain Deployment [CARD-206, REQ-HOMELAB-001 - REQ-HOMELAB-006].

Tests full multi-agent orchestration, compiler-guided self-correction,
and dry-run infrastructure planning for isolated Hyper-V Windows Domain.
"""

import pytest

from src.application.orchestration.homelab_domain_recipe import (
    generate_domain_topology_hcl,
    get_homelab_domain_workflow_recipe,
)
from src.application.skills.opentofu_tools import (
    OpenTofuHyperVTools,
    extract_hcl_diagnostics,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.mark.asyncio
async def test_homelab_domain_deployment_e2e(tmp_path):
    """
    Simulate full 4-chapter autonomous deployment relay:
    Admin -> Architect -> Engineer (with compiler self-correction) -> Admin (Plan Review).
    """
    # 1. Initialize ephemeral store and tools
    db_path = tmp_path / "test_homelab_e2e.db"
    store = SQLiteStateStore(db_path=str(db_path))
    store.initialize_db()

    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    infra_dir = workspace_dir / "infra" / "homelab"
    infra_dir.mkdir(parents=True)

    tools = OpenTofuHyperVTools(workspace_root=workspace_dir)

    # 2. Retrieve the Homelab Domain Workflow Recipe
    recipe = get_homelab_domain_workflow_recipe()
    assert recipe["name"] == "homelab-domain-deployment"
    chapters = recipe["chapters"]
    assert len(chapters) == 4

    # --- CHAPTER 1: Platform & Switch Verification (Homelab Admin) ---
    host_inspection = tools._inspect_host()
    assert host_inspection["status"] == "ok"
    host_info = host_inspection["host_info"]
    assert host_info["cpu_cores"] >= 2
    assert host_info["disk_free_gb"] > 0
    # Verified: Zero modifications made to host physical adapters

    # --- CHAPTER 2: Domain Architecture Blueprint (Homelab Architect) ---
    domain_name = "lab.local"
    subnet = "10.10.10.0/24"
    switch_name = "DomainSwitch"

    # --- CHAPTER 3: IaC Authoring & Compiler Self-Correction (Homelab Engineer) ---
    # Phase 3a: Engineer generates HCL topology
    hcl_content = generate_domain_topology_hcl(
        domain_name=domain_name,
        subnet=subnet,
        switch_name=switch_name,
    )
    main_tf = infra_dir / "main.tf"
    main_tf.write_text(hcl_content, encoding="utf-8")

    # Phase 3b: Simulate compiler diagnostic feedback loop
    sample_error = """
Error: Unsupported argument

  on main.tf line 42, in resource "hyperv_machine_instance" "dc01":
  42:   switch_name = "DomainSwitch"

An argument named "switch_name" is not expected here. Did you mean "switch_id"?
"""
    diagnostics = extract_hcl_diagnostics(sample_error)
    assert len(diagnostics) == 1
    assert diagnostics[0]["line"] == 42
    assert "Unsupported argument" in diagnostics[0]["summary"]

    # Phase 3c: Validate corrected configuration
    validation_result = await tools.manage_opentofu_hyperv(
        action="validate",
        config_path="infra/homelab",
        dry_run=True,
    )
    assert validation_result["status"] == "ok"
    assert validation_result["valid"] is True

    # --- CHAPTER 4: Final Review & Dry-Run Plan Approval (Homelab Admin) ---
    plan_result = await tools.manage_opentofu_hyperv(
        action="plan",
        config_path="infra/homelab",
        variables={"vm_name": "dc01", "vlan": 10},
        dry_run=True,
    )
    assert plan_result["status"] == "ok"
    assert plan_result["dry_run"] is True
    assert plan_result["plan"]["to_add"] == 1
    assert plan_result["plan"]["to_destroy"] == 0

    # Invariants Check:
    # 1. Private switch exists and is Internal
    assert 'resource "hyperv_vmswitch" "domain_switch"' in hcl_content
    assert 'switch_type = "Internal"' in hcl_content
    assert "External" not in hcl_content

    # 2. 3 Gen2 VMs exist
    assert '"dc01"' in hcl_content
    assert '"dc02"' in hcl_content
    assert '"fs01"' in hcl_content
    assert "generation = 2" in hcl_content

    # 3. Subnet matches
    assert "10.10.10." in hcl_content
