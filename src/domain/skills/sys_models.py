"""
Domain models for Sysadmin & System Inspection Skill.
"""

from pydantic import BaseModel, Field


class SystemInfoReport(BaseModel):
    os_name: str = Field(description="Operating System name")
    platform_release: str = Field(description="Kernel / OS release version")
    architecture: str = Field(description="Machine architecture (e.g. x86_64, aarch64)")
    cpu_count: int = Field(description="Number of logical CPU cores")
    memory_total_gb: float = Field(description="Total RAM in Gigabytes")
    memory_available_gb: float = Field(description="Available RAM in Gigabytes")
    memory_percent_used: float = Field(description="Percentage of RAM utilized")
    disk_total_gb: float = Field(description="Total Disk capacity in Gigabytes")
    disk_free_gb: float = Field(description="Free Disk capacity in Gigabytes")
    uptime_seconds: float = Field(description="Host uptime in seconds")
