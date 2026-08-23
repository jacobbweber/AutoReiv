"""
Domain Models for Settings, Purpose Matrix, and Hardware Fit Calculator [REQ-SETTINGS-001, REQ-SETTINGS-002, REQ-SETTINGS-004].
"""

from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class ModelPurpose(str, Enum):
    GENERAL = "general"
    REASONING = "reasoning"
    TASK_EXECUTION = "task_execution"
    VISION = "vision"
    AUXILIARY = "auxiliary"
    FAST = "fast"


class FitStatus(str, Enum):
    OPTIMAL = "optimal"
    RUNNABLE = "runnable"
    OFFLOADED = "offloaded"
    INSUFFICIENT_MEMORY = "insufficient_memory"


class ModelDescriptor(BaseModel):
    id: str = Field(description="Fully qualified model identifier (e.g. ollama/qwen2.5:32b)")
    name: str = Field(description="Short model name (e.g. qwen2.5:32b)")
    provider: str = Field(description="Provider name (e.g. ollama, openai)")
    param_size_b: Optional[float] = Field(default=None, description="Model parameter count in billions")
    quantization: str = Field(default="Q4_K_M", description="Quantization level")
    family: str = Field(default="unknown", description="Model architecture family (e.g. qwen2, llama)")
    is_multimodal: bool = Field(default=False, description="Whether the model supports vision/image inputs")


class HardwareSpecs(BaseModel):
    total_ram_gb: float = Field(description="Total system RAM in GB")
    available_ram_gb: float = Field(description="Currently available system RAM in GB")
    vram_gb: float = Field(default=0.0, description="Dedicated GPU VRAM in GB")
    cpu_cores: int = Field(default=4, description="Number of logical CPU cores")
    is_unified_memory: bool = Field(
        default=True, description="Whether system uses unified memory (e.g. Apple Silicon, Nimo PC)"
    )
    platform_name: str = Field(default="Linux", description="Operating system / platform name")


class ModelFitReport(BaseModel):
    model_id: str = Field(description="Evaluated model ID")
    param_size_b: float = Field(description="Parameter count in billions")
    quantization: str = Field(description="Quantization format")
    required_ram_gb: float = Field(description="Estimated RAM in GB required for weights + KV cache")
    available_ram_gb: float = Field(description="Available RAM in GB on the host")
    fit_status: FitStatus = Field(description="Fit classification")
    recommendation_score: float = Field(default=0.0, description="Suitability score from 0.0 to 100.0")
    notes: str = Field(default="", description="Human-readable assessment and performance guidance")


class ModelPurposeMatrix(BaseModel):
    default_model: str = Field(default="default", description="Global fallback model")
    purposes: Dict[ModelPurpose, str] = Field(default_factory=dict, description="Purpose to model ID bindings")


class AgentCustomization(BaseModel):
    agent_id: str
    tone: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    allowed_tool_names: Optional[list[str]] = None
    max_turns: Optional[int] = None


class MCPServerConfig(BaseModel):
    name: str
    command: list[str]
    env: Optional[Dict[str, str]] = None
    enabled: bool = True
