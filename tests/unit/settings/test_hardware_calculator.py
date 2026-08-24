"""
Unit tests for Hardware Fit Calculator & RAM Estimation [REQ-SETTINGS-003, REQ-SETTINGS-004].
"""

from src.application.settings.hardware_calculator import HardwareFitCalculator
from src.domain.settings.models import FitStatus, HardwareSpecs


def test_hardware_specs_auto_detection():
    calc = HardwareFitCalculator()
    specs = calc.get_hardware_specs()

    assert specs.total_ram_gb > 0
    assert specs.cpu_cores >= 1
    assert specs.platform_name != ""


def test_hardware_specs_with_custom_override():
    calc = HardwareFitCalculator()
    custom = HardwareSpecs(
        total_ram_gb=128.0,
        available_ram_gb=115.0,
        cpu_cores=16,
        is_unified_memory=True,
        platform_name="Ubuntu Linux (Nimo 2L)",
    )
    specs = calc.get_hardware_specs(override=custom)
    assert specs.total_ram_gb == 128.0
    assert specs.cpu_cores == 16


def test_estimate_model_ram():
    calc = HardwareFitCalculator()

    # 7B at Q4_K_M (~4.5 - 6.5 GB)
    ram_7b_q4 = calc.estimate_model_ram(param_size_b=7.0, quantization="Q4_K_M")
    assert 4.0 <= ram_7b_q4 <= 7.5

    # 32B at Q4_K_M (~20 - 25 GB)
    ram_32b_q4 = calc.estimate_model_ram(param_size_b=32.0, quantization="Q4_K_M")
    assert 20.0 <= ram_32b_q4 <= 28.0

    # 70B at Q4_K_M (~40 - 50 GB)
    ram_70b_q4 = calc.estimate_model_ram(param_size_b=70.0, quantization="Q4_K_M")
    assert 40.0 <= ram_70b_q4 <= 55.0

    # 70B at FP16 (>140 GB)
    ram_70b_fp16 = calc.estimate_model_ram(param_size_b=70.0, quantization="FP16")
    assert ram_70b_fp16 > 140.0


def test_evaluate_fit_on_128gb_nimo_host():
    calc = HardwareFitCalculator()
    nimo_specs = HardwareSpecs(
        total_ram_gb=128.0,
        available_ram_gb=115.0,
        cpu_cores=16,
        is_unified_memory=True,
        platform_name="Ubuntu Linux (Nimo 2L)",
    )

    # 70B Q4 should be OPTIMAL on 128GB Nimo PC
    report_70b = calc.evaluate_fit(
        param_size_b=70.0,
        quantization="Q4_K_M",
        specs=nimo_specs,
        model_id="ollama/qwen2.5:70b",
    )
    assert report_70b.fit_status == FitStatus.OPTIMAL
    assert report_70b.recommendation_score >= 90.0

    # 70B FP16 requires ~160GB, exceeding 128GB total RAM -> INSUFFICIENT_MEMORY
    report_70b_fp16 = calc.evaluate_fit(
        param_size_b=70.0,
        quantization="FP16",
        specs=nimo_specs,
        model_id="ollama/qwen2.5:70b-fp16",
    )
    assert report_70b_fp16.fit_status == FitStatus.INSUFFICIENT_MEMORY
    assert report_70b_fp16.recommendation_score == 0.0


def test_evaluate_fit_on_16gb_laptop():
    calc = HardwareFitCalculator()
    laptop_specs = HardwareSpecs(
        total_ram_gb=16.0,
        available_ram_gb=10.0,
        cpu_cores=8,
        is_unified_memory=False,
    )

    # 3B Q4 should fit
    report_3b = calc.evaluate_fit(
        param_size_b=3.0,
        quantization="Q4_K_M",
        specs=laptop_specs,
        model_id="ollama/llama3.2:3b",
    )
    assert report_3b.fit_status in (FitStatus.OPTIMAL, FitStatus.RUNNABLE)

    # 32B Q4 (~22GB) exceeds 16GB total -> INSUFFICIENT_MEMORY
    report_32b = calc.evaluate_fit(
        param_size_b=32.0,
        quantization="Q4_K_M",
        specs=laptop_specs,
        model_id="ollama/qwen2.5:32b",
    )
    assert report_32b.fit_status == FitStatus.INSUFFICIENT_MEMORY
