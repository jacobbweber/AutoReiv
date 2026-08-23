"""
Hardware Fit Calculator & RAM Estimation Engine [REQ-SETTINGS-003, REQ-SETTINGS-004].
"""

import os
import platform
from typing import ClassVar, Dict, Optional

try:
    import psutil
except ImportError:
    psutil = None

from src.domain.settings.models import FitStatus, HardwareSpecs, ModelFitReport


class HardwareFitCalculator:
    """
    Analyzes host hardware capacity and calculates RAM requirements
    for local LLM parameter sizes and quantization formats.
    """

    BYTES_PER_WEIGHT: ClassVar[Dict[str, float]] = {
        "q4_k_m": 0.55,
        "q4_0": 0.55,
        "q4_1": 0.58,
        "q4_k_s": 0.53,
        "q4": 0.55,
        "q5_k_m": 0.68,
        "q5_0": 0.68,
        "q5_1": 0.70,
        "q5": 0.68,
        "q8_0": 1.05,
        "q8_k": 1.05,
        "q8": 1.05,
        "fp8": 1.00,
        "fp16": 2.00,
        "bf16": 2.00,
    }

    def get_hardware_specs(self, override: Optional[HardwareSpecs] = None) -> HardwareSpecs:
        """
        Auto-detect host hardware specifications, or return custom override specs.
        """
        if override is not None:
            return override

        total_gb = 16.0
        avail_gb = 12.0

        if psutil is not None:
            try:
                mem = psutil.virtual_memory()
                total_gb = mem.total / (1024**3)
                avail_gb = mem.available / (1024**3)
            except Exception:
                pass

        cores = os.cpu_count() or 4
        plat_name = f"{platform.system()} {platform.release()}"

        return HardwareSpecs(
            total_ram_gb=round(total_gb, 1),
            available_ram_gb=round(avail_gb, 1),
            cpu_cores=cores,
            is_unified_memory=True if "Linux" in plat_name or "Darwin" in plat_name else False,
            platform_name=plat_name,
        )

    def estimate_model_ram(
        self,
        param_size_b: float,
        quantization: str = "Q4_K_M",
        context_k_tokens: int = 8,
    ) -> float:
        """
        Calculate total RAM required (weights + KV cache overhead).
        """
        bpw = self.BYTES_PER_WEIGHT.get(quantization.lower(), 0.60)
        weight_ram = param_size_b * bpw * 1.15
        kv_cache = (context_k_tokens / 8.0) * (param_size_b / 7.0) * 1.0 + 0.5
        return round(weight_ram + kv_cache, 2)

    def evaluate_fit(
        self,
        param_size_b: float,
        quantization: str = "Q4_K_M",
        specs: Optional[HardwareSpecs] = None,
        model_id: str = "custom",
    ) -> ModelFitReport:
        """
        Evaluate if a model can run comfortably on the target hardware.
        """
        hardware = self.get_hardware_specs(override=specs)
        required_ram = self.estimate_model_ram(param_size_b, quantization)
        available_ram = hardware.available_ram_gb

        if required_ram > hardware.total_ram_gb:
            return ModelFitReport(
                model_id=model_id,
                param_size_b=param_size_b,
                quantization=quantization,
                required_ram_gb=required_ram,
                available_ram_gb=available_ram,
                fit_status=FitStatus.INSUFFICIENT_MEMORY,
                recommendation_score=0.0,
                notes="Exceeds total system RAM. Model cannot run without crashing or severe OOM.",
            )

        if available_ram >= required_ram * 1.25 or (
            hardware.is_unified_memory and hardware.total_ram_gb >= required_ram * 1.5
        ):
            return ModelFitReport(
                model_id=model_id,
                param_size_b=param_size_b,
                quantization=quantization,
                required_ram_gb=required_ram,
                available_ram_gb=available_ram,
                fit_status=FitStatus.OPTIMAL,
                recommendation_score=95.0,
                notes="Optimal fit. Model fits fully in fast memory with abundant headroom.",
            )

        if available_ram >= required_ram:
            return ModelFitReport(
                model_id=model_id,
                param_size_b=param_size_b,
                quantization=quantization,
                required_ram_gb=required_ram,
                available_ram_gb=available_ram,
                fit_status=FitStatus.RUNNABLE,
                recommendation_score=75.0,
                notes="Runnable. Model fits in available RAM with modest headroom.",
            )

        return ModelFitReport(
            model_id=model_id,
            param_size_b=param_size_b,
            quantization=quantization,
            required_ram_gb=required_ram,
            available_ram_gb=available_ram,
            fit_status=FitStatus.OFFLOADED,
            recommendation_score=45.0,
            notes="Fits within total system RAM but may require memory page swapping.",
        )
