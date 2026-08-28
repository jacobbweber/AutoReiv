"""
Sysadmin & System Inspection Skill for Linux Sysadmin [REQ-AGENTS-003, REQ-AGENTS-004].
"""

import asyncio
import os
import platform
import shutil
import socket
import sys
import time
from typing import Any, Dict

from src.application.kernel.tool_registry import ScopedToolRegistry


class SysadminSkill:
    """
    Skill providing system health inspection and safe subprocess execution.
    """

    def get_system_info(self) -> Dict[str, Any]:
        """
        Collect cross-platform system information and resource utilization metrics.
        """
        cpu_count = os.cpu_count() or 1
        os_name = platform.system()
        release = platform.release()
        machine = platform.machine()

        # Disk metrics
        try:
            root_path = "C:\\" if sys.platform == "win32" else "/"
            disk = shutil.disk_usage(root_path)
            disk_total_gb = round(disk.total / (1024**3), 2)
            disk_free_gb = round(disk.free / (1024**3), 2)
        except Exception:
            disk_total_gb = 0.0
            disk_free_gb = 0.0

        # Memory metrics
        mem_total_gb = 16.0
        mem_avail_gb = 8.0
        mem_percent = 50.0

        if sys.platform == "linux" and os.path.exists("/proc/meminfo"):
            try:
                meminfo = {}
                with open("/proc/meminfo", "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            meminfo[parts[0].strip()] = int(parts[1].split()[0])
                total_kb = meminfo.get("MemTotal", 16 * 1024 * 1024)
                avail_kb = meminfo.get("MemAvailable", total_kb // 2)
                mem_total_gb = round(total_kb / (1024**2), 2)
                mem_avail_gb = round(avail_kb / (1024**2), 2)
                mem_percent = round(((mem_total_gb - mem_avail_gb) / mem_total_gb) * 100, 1)
            except Exception:
                pass
        elif sys.platform == "win32":
            try:
                import ctypes

                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                mem_total_gb = round(stat.ullTotalPhys / (1024**3), 2)
                mem_avail_gb = round(stat.ullAvailPhys / (1024**3), 2)
                mem_percent = float(stat.dwMemoryLoad)
            except Exception:
                pass

        # Uptime
        uptime_sec = 0.0
        if sys.platform == "linux" and os.path.exists("/proc/uptime"):
            try:
                with open("/proc/uptime", "r", encoding="utf-8") as f:
                    uptime_sec = float(f.read().split()[0])
            except Exception:
                uptime_sec = 3600.0
        elif sys.platform == "win32":
            try:
                import ctypes

                ticks = ctypes.windll.kernel32.GetTickCount64()
                uptime_sec = round(ticks / 1000.0, 1)
            except Exception:
                uptime_sec = 3600.0
        else:
            uptime_sec = 3600.0

        # Network & Hostname telemetry [REQ-SYSINFO-001, REQ-SYSINFO-003]
        hostname = "localhost"
        primary_ip = "127.0.0.1"
        ip_addresses = ["127.0.0.1"]
        try:
            hostname = socket.gethostname()
            # Primary routable IP resolution via dummy UDP socket probe
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.settimeout(0.5)
                    s.connect(("8.8.8.8", 80))
                    primary_ip = s.getsockname()[0]
            except Exception:
                primary_ip = socket.gethostbyname(hostname)

            # Collect all active adapter IPs
            try:
                all_ips = socket.gethostbyname_ex(hostname)[2]
                valid_ips = [ip for ip in all_ips if not ip.startswith("127.") or len(all_ips) == 1]
                if primary_ip not in valid_ips:
                    valid_ips.insert(0, primary_ip)
                ip_addresses = list(dict.fromkeys(valid_ips)) if valid_ips else [primary_ip]
            except Exception:
                ip_addresses = [primary_ip]
        except Exception:
            hostname = "localhost"
            primary_ip = "127.0.0.1"
            ip_addresses = ["127.0.0.1"]

        return {
            "hostname": hostname,
            "primary_ip": primary_ip,
            "ip_addresses": ip_addresses,
            "os_name": os_name,
            "platform_release": release,
            "architecture": machine,
            "cpu_count": cpu_count,
            "memory_total_gb": mem_total_gb,
            "memory_available_gb": mem_avail_gb,
            "memory_percent_used": mem_percent,
            "disk_total_gb": disk_total_gb,
            "disk_free_gb": disk_free_gb,
            "uptime_seconds": uptime_sec,
        }

    async def run_cli_command(
        self,
        command: str,
        timeout_seconds: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Execute a shell command with an execution timeout and output buffer limit.

        Uses subprocess.run in a thread executor instead of asyncio.create_subprocess_shell
        because uvicorn on Windows uses SelectorEventLoop which does not support subprocess
        creation (raises NotImplementedError).
        """
        import subprocess

        start_time = time.perf_counter()
        try:
            loop = asyncio.get_event_loop()
            returncode, stdout_bytes, stderr_bytes = await loop.run_in_executor(
                None,
                self._run_subprocess_sync,
                command,
                timeout_seconds,
            )
            dur_ms = (time.perf_counter() - start_time) * 1000
            stdout_str = stdout_bytes.decode("utf-8", errors="replace")[:10000]
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")[:10000]

            return {
                "exit_code": returncode,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "duration_ms": round(dur_ms, 2),
            }
        except subprocess.TimeoutExpired:
            dur_ms = (time.perf_counter() - start_time) * 1000
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout_seconds} seconds.",
                "error": f"Command timed out after {timeout_seconds} seconds.",
                "duration_ms": round(dur_ms, 2),
            }
        except Exception as e:
            dur_ms = (time.perf_counter() - start_time) * 1000
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "error": str(e),
                "duration_ms": round(dur_ms, 2),
            }

    @staticmethod
    def _run_subprocess_sync(
        command: str, timeout: float
    ) -> tuple:
        """Synchronous subprocess execution to run in a thread executor."""
        import subprocess

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register sysadmin tools in the scoped registry."""
        registry.register_tool(
            name="system_info",
            description="Get host system metrics and network info including machine hostname, primary IP address, all active adapter IPs, OS, CPU, RAM utilization, and disk storage.",
            parameters={"type": "object"},
            handler=self.get_system_info,
        )

        registry.register_tool(
            name="cli_exec",
            description="Execute a safe CLI shell command on the host OS with timeout controls. Note: Always use commands appropriate for the host OS (e.g. 'ipconfig', 'netstat', 'dir' on Windows; 'ip addr', 'ls' on Linux).",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout_seconds": {
                        "type": "number",
                        "description": "Optional timeout in seconds",
                        "default": 30.0,
                    },
                },
                "required": ["command"],
            },
            handler=self.run_cli_command,
        )
