"""
Unit tests for Settings Domain Models [REQ-SETTINGS-001, REQ-SETTINGS-002, REQ-SETTINGS-004].
"""

from src.domain.settings.models import (
    FitStatus,
    HardwareSpecs,
    ModelDescriptor,
    ModelFitReport,
    ModelPurpose,
    ModelPurposeMatrix,
)


def test_model_descriptor_instantiation():
    desc = ModelDescriptor(
        id="ollama/qwen2.5:32b",
        name="qwen2.5:32b",
        provider="ollama",
        param_size_b=32.0,
        quantization="Q4_K_M",
        family="qwen2",
        is_multimodal=False,
    )
    assert desc.id == "ollama/qwen2.5:32b"
    assert desc.param_size_b == 32.0
    assert desc.quantization == "Q4_K_M"


def test_model_purpose_matrix():
    matrix = ModelPurposeMatrix(
        default_model="ollama/qwen2.5:7b",
        purposes={
            ModelPurpose.REASONING: "ollama/qwen2.5:32b",
            ModelPurpose.FAST: "ollama/qwen2.5:3.8b",
            ModelPurpose.TASK_EXECUTION: "ollama/qwen2.5:14b",
        },
    )
    assert matrix.default_model == "ollama/qwen2.5:7b"
    assert matrix.purposes[ModelPurpose.REASONING] == "ollama/qwen2.5:32b"
    assert matrix.purposes[ModelPurpose.FAST] == "ollama/qwen2.5:3.8b"


def test_hardware_specs():
    specs = HardwareSpecs(
        total_ram_gb=128.0,
        available_ram_gb=110.0,
        vram_gb=0.0,
        cpu_cores=16,
        is_unified_memory=True,
        platform_name="Ubuntu Linux (Nimo 2L)",
    )
    assert specs.total_ram_gb == 128.0
    assert specs.is_unified_memory is True
    assert specs.cpu_cores == 16


def test_model_fit_report():
    report = ModelFitReport(
        model_id="ollama/qwen2.5:70b",
        param_size_b=70.0,
        quantization="Q4_K_M",
        required_ram_gb=43.5,
        available_ram_gb=110.0,
        fit_status=FitStatus.OPTIMAL,
        recommendation_score=95.0,
        notes="Fits comfortably in unified memory.",
    )
    assert report.fit_status == FitStatus.OPTIMAL
    assert report.recommendation_score == 95.0
    assert report.required_ram_gb == 43.5
