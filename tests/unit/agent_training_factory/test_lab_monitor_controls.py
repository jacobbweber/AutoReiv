"""
Unit tests for Lab Monitor controls and job inputs extraction [CARD-182, REQ-LAB-001, REQ-LAB-002, REQ-LAB-003].
"""

from fastapi.testclient import TestClient

from src.domain.orchestration.factory_packets import FactoryJob, FactoryPacket, WorkPacket
from src.web.app import create_app
from src.web.routers.agent_training_factory import extract_job_initial_inputs


def test_extract_job_initial_inputs():
    job = FactoryJob(
        id="fjob_test_123",
        target_agent_id="hyperv",
        session_id="sess_123",
        status="failed",
        seed_intent="Train capabilities for hyperv",
        objectives=["manage VMs", "checkpoints"],
        target_host="192.168.1.100",
    )

    work_pkt = WorkPacket(
        goal="Train capabilities for hyperv",
        target_agent_id="hyperv",
        facts=["manage VMs", "checkpoints"],
        constraints=[
            "risk_policy=ask",
            "deliverable_type=mcp",
            "constraints=Banned: rm -rf",
            "prerequisites=Hyper-V module",
            "reference_docs=https://learn.microsoft.com/virtualization/hyper-v-on-windows/",
        ],
        done_when="Sandbox passes",
        target_host="192.168.1.100",
        target_directory="C:\\VMs",
    )

    envelope = FactoryPacket(
        id="fpkt_initial_work",
        job_id=job.id,
        packet_type="work",
        sender_role="orchestrator",
        recipient_role="intent_distill",
        node_id="intent_distill",
        payload=work_pkt.model_dump(),
    )

    inputs = extract_job_initial_inputs(job, [envelope])

    assert inputs["target_agent_id"] == "hyperv"
    assert inputs["seed_intent"] == "Train capabilities for hyperv"
    assert inputs["deliverable_type"] == "mcp"
    assert inputs["constraints"] == "Banned: rm -rf"
    assert inputs["prerequisites"] == "Hyper-V module"
    assert inputs["reference_docs"] == "https://learn.microsoft.com/virtualization/hyper-v-on-windows/"
    assert inputs["target_host"] == "192.168.1.100"
    assert inputs["target_directory"] == "C:\\VMs"


def test_get_factory_job_exposes_inputs():
    app = create_app()
    client = TestClient(app)

    # 1. Create a job with advanced requirements
    res = client.post(
        "/api/agent_training_factory/jobs",
        json={
            "target_agent_id": "test-hyperv",
            "seed_intent": "Manage Hyper-V VMs",
            "deliverable_type": "mcp",
            "constraints": "No raw delete",
            "prerequisites": "powershell.exe",
            "reference_docs": "docs/hyperv.md",
        },
    )
    assert res.status_code == 200
    job_id = res.json()["job_id"]

    # 2. Query job details via GET /api/agent_training_factory/jobs/{id}
    detail_res = client.get(f"/api/agent_training_factory/jobs/{job_id}")
    assert detail_res.status_code == 200
    data = detail_res.json()

    assert "inputs" in data
    inputs = data["inputs"]
    assert inputs["target_agent_id"] == "test-hyperv"
    assert inputs["seed_intent"] == "Manage Hyper-V VMs"
    assert inputs["deliverable_type"] == "mcp"
    assert inputs["constraints"] == "No raw delete"
    assert inputs["prerequisites"] == "powershell.exe"
    assert inputs["reference_docs"] == "docs/hyperv.md"
