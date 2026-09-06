"""Hyper-V focused tool source builders for ToolSynthesizer (CARD-171)."""
from __future__ import annotations

import json
from typing import List, Optional

ACTIONS = {
    "vm": ["status","list","get","create","start","stop","restart","checkpoint","snapshot","list_checkpoints","restore_checkpoint","remove_checkpoint","delete","remove","execute_ps"],
    "network": ["status","list_switches","create_switch","remove_switch","attach_nic","detach_nic","execute_ps"],
    "unattend": ["status","build_autounattend","build_autounattend_iso","mount_os_iso","mount_answer_iso","create_template_vm","execute_ps"],
    "template": ["status","list_templates","checkpoint_template","export_template","start_maintenance","stop_maintenance","execute_ps"],
    "full": ["status","list","get","create","start","stop","restart","checkpoint","snapshot","list_checkpoints","restore_checkpoint","remove_checkpoint","delete","remove","list_switches","create_switch","remove_switch","attach_nic","detach_nic","build_autounattend","build_autounattend_iso","mount_os_iso","mount_answer_iso","create_template_vm","list_templates","checkpoint_template","export_template","start_maintenance","stop_maintenance","execute_ps"],
}

def build_hyperv_python_tool(agent_id, tool_name, seed_intent, objectives=None, focus="full"):
    focus = focus if focus in ACTIONS else "full"
    objs_str = json.dumps(list(objectives or []))[1:-1]
    valid_repr = json.dumps(ACTIONS[focus])
    intent = (seed_intent or "").replace('"""', "'")
    # Docstrings must not contain raw Windows paths / Hyper-V\ escapes.
    intent = intent.replace("\\", "/").replace("\n", " ").strip()
    agent_u = agent_id.upper()
    L = []
    A = L.append
    A('"""\n')
    A(f"{agent_u} Operational Automation Tool [REQ-FACT-009, REQ-FACT-017].\n")
    A(f"Provides automated PowerShell execution for {intent}.\n")
    A(f"Focus: {focus}.\n")
    A('"""\n\n')
    A("import json\nimport logging\nimport os\nfrom pathlib import Path\nimport subprocess\nfrom typing import Any, Dict, List, Optional\n\n")
    A("logger = logging.getLogger(__name__)\n\n")
    A(f"OBJECTIVES: List[str] = [{objs_str}]\n")
    A(f'FOCUS = "{focus}"\n\n')
    A("""def _run_powershell(script: str, timeout: float = 120.0) -> Dict[str, Any]:
    full_cmd = "Import-Module Hyper-V -ErrorAction SilentlyContinue; " + script
    try:
        proc = subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-ExecutionPolicy","Bypass","-Command",full_cmd], capture_output=True, text=True, timeout=timeout)
        stdout = proc.stdout.strip(); stderr = proc.stderr.strip(); parsed_data = None
        if stdout:
            try: parsed_data = json.loads(stdout)
            except Exception: parsed_data = stdout
        return {"success": proc.returncode == 0, "returncode": proc.returncode, "stdout": stdout, "stderr": stderr, "data": parsed_data}
    except subprocess.TimeoutExpired:
        return {"success": False, "returncode": -1, "stdout": "", "stderr": f"PowerShell command timed out after {timeout}s", "data": None}
    except Exception as exc:
        return {"success": False, "returncode": -1, "stdout": "", "stderr": str(exc), "data": None}

def _escape_ps(value: str) -> str:
    return str(value).replace("'", "''")

""")
    A(f"def {tool_name}(\n")
    A("    action: str = \"status\",\n")
    A("    name: Optional[str] = None,\n")
    A("    memory: Optional[str] = \"2GB\",\n")
    A("    vcpus: int = 2,\n")
    A("    generation: int = 2,\n")
    A("    switch_name: Optional[str] = None,\n")
    A("    switch_type: Optional[str] = \"Internal\",\n")
    A("    vhd_path: Optional[str] = None,\n")
    A("    snapshot_name: Optional[str] = None,\n")
    A("    iso_path: Optional[str] = r\"D:\\\\Archive\\\\Tech\\\\Labs\\\\installers\\\\2022.ISO\",\n")
    A("    answer_iso_path: Optional[str] = None,\n")
    A("    unattend_path: Optional[str] = None,\n")
    A("    output_dir: Optional[str] = None,\n")
    A("    export_path: Optional[str] = None,\n")
    A("    command: Optional[str] = None,\n")
    A("    dry_run: bool = False,\n")
    A("    **kwargs: Any,\n")
    A(f") -> Dict[str, Any]:\n")
    A(f'    """Manage {agent_id} Hyper-V automation (focus={focus}) via qualified Hyper-V\\\\ cmdlets."""\n')
    A(f"    valid_actions = {valid_repr}\n")
    A("    if action not in valid_actions:\n")
    A("        raise ValueError(f\"Invalid action '{action}'. Allowed: {valid_actions}\")\n")
    A("""    mem_clean = str(memory).upper().replace(" ", "")
    mem_bytes = 2147483648
    if mem_clean.endswith("GB"):
        try: mem_bytes = int(float(mem_clean[:-2]) * 1024 * 1024 * 1024)
        except Exception: pass
    elif mem_clean.endswith("MB"):
        try: mem_bytes = int(float(mem_clean[:-2]) * 1024 * 1024)
        except Exception: pass
    out_dir = output_dir or str(Path.cwd() / "hyperv_unattend")
    unattend_file = unattend_path or str(Path(out_dir) / "Autounattend.xml")
    answer_iso = answer_iso_path or str(Path(out_dir) / "autounattend.iso")

""")
    A("""    if action in ("status", "list"):
        if name:
            ps_cmd = "Hyper-V\\\\Get-VM -Name '" + _escape_ps(name) + "' | Select-Object Name, State, CPUUsage, MemoryAssigned, Uptime, Status, Id, Generation | ConvertTo-Json -Compress"
        else:
            ps_cmd = "Hyper-V\\\\Get-VM | Select-Object Name, State, CPUUsage, MemoryAssigned, Uptime, Status, Id, Generation | ConvertTo-Json -Compress"
    elif action == "get":
        if not name: raise ValueError("Action 'get' requires 'name' parameter")
        ps_cmd = "Hyper-V\\\\Get-VM -Name '" + _escape_ps(name) + "' | Select-Object Name, State, CPUUsage, MemoryAssigned, Uptime, Status, Id, Generation, NetworkAdapters | ConvertTo-Json"
    elif action == "create":
        if not name: raise ValueError("Action 'create' requires 'name' parameter")
        ps_cmd = "$vmName = '" + _escape_ps(name) + "'; Hyper-V\\\\New-VM -Name $vmName -MemoryStartupBytes " + str(mem_bytes) + " -Generation " + str(generation)
        if switch_name: ps_cmd += " -SwitchName '" + _escape_ps(switch_name) + "'"
        if vhd_path: ps_cmd += "; Hyper-V\\\\New-VHD -Path '" + _escape_ps(vhd_path) + "' -SizeBytes 42949672960 -Dynamic; Hyper-V\\\\Add-VMHardDiskDrive -VMName $vmName -Path '" + _escape_ps(vhd_path) + "'"
        ps_cmd += "; Hyper-V\\\\Get-VM -Name $vmName | ConvertTo-Json -Compress"
    elif action == "start":
        if not name: raise ValueError("Action 'start' requires 'name' parameter")
        ps_cmd = "Hyper-V\\\\Start-VM -Name '" + _escape_ps(name) + "' -PassThru | Select-Object Name, State | ConvertTo-Json -Compress"
    elif action == "stop":
        if not name: raise ValueError("Action 'stop' requires 'name' parameter")
        ps_cmd = "Hyper-V\\\\Stop-VM -Name '" + _escape_ps(name) + "' -Force -PassThru | Select-Object Name, State | ConvertTo-Json -Compress"
    elif action == "restart":
        if not name: raise ValueError("Action 'restart' requires 'name' parameter")
        ps_cmd = "Hyper-V\\\\Restart-VM -Name '" + _escape_ps(name) + "' -Force; Hyper-V\\\\Get-VM -Name '" + _escape_ps(name) + "' | Select-Object Name, State | ConvertTo-Json -Compress"
    elif action in ("checkpoint", "snapshot", "checkpoint_template"):
        if not name: raise ValueError(f"Action '{action}' requires 'name' parameter")
        snap = snapshot_name or (str(name) + "_checkpoint")
        ps_cmd = "Hyper-V\\\\Checkpoint-VM -Name '" + _escape_ps(name) + "' -SnapshotName '" + _escape_ps(snap) + "'; Hyper-V\\\\Get-VMSnapshot -VMName '" + _escape_ps(name) + "' | ConvertTo-Json -Compress"
    elif action == "list_checkpoints":
        if not name: raise ValueError("Action 'list_checkpoints' requires 'name' parameter")
        ps_cmd = (
            "Hyper-V\\\\Get-VMSnapshot -VMName '" + _escape_ps(name) + "' | "
            "Select-Object VMName, Name, CreationTime, ParentSnapshotName, SnapshotType | ConvertTo-Json -Compress"
        )
    elif action == "restore_checkpoint":
        if not name: raise ValueError("Action 'restore_checkpoint' requires 'name' parameter")
        if not snapshot_name: raise ValueError("Action 'restore_checkpoint' requires 'snapshot_name' parameter")
        ps_cmd = (
            "Hyper-V\\\\Get-VMSnapshot -VMName '" + _escape_ps(name) + "' -Name '" + _escape_ps(snapshot_name) + "' | "
            "Hyper-V\\\\Restore-VMSnapshot -Confirm:$false; "
            "Hyper-V\\\\Get-VMSnapshot -VMName '" + _escape_ps(name) + "' | Select-Object VMName, Name, CreationTime | ConvertTo-Json -Compress"
        )
    elif action == "remove_checkpoint":
        if not name: raise ValueError("Action 'remove_checkpoint' requires 'name' parameter")
        if not snapshot_name: raise ValueError("Action 'remove_checkpoint' requires 'snapshot_name' parameter")
        ps_cmd = (
            "Hyper-V\\\\Get-VMSnapshot -VMName '" + _escape_ps(name) + "' -Name '" + _escape_ps(snapshot_name) + "' | "
            "Hyper-V\\\\Remove-VMSnapshot -Confirm:$false; "
            "@{success=$true; action='remove_checkpoint'; vm='" + _escape_ps(name) + "'; snapshot='" + _escape_ps(snapshot_name) + "'} | ConvertTo-Json -Compress"
        )
    elif action in ("delete", "remove"):
        if not name: raise ValueError(f"Action '{action}' requires 'name' parameter")
        ps_cmd = "Hyper-V\\\\Remove-VM -Name '" + _escape_ps(name) + "' -Force"
    elif action == "list_switches":
        ps_cmd = "Hyper-V\\\\Get-VMSwitch | Select-Object Name, SwitchType, NetAdapterInterfaceDescription | ConvertTo-Json -Compress"
    elif action == "create_switch":
        if not switch_name: raise ValueError("Action 'create_switch' requires 'switch_name' parameter")
        st = switch_type or "Internal"
        ps_cmd = "Hyper-V\\\\New-VMSwitch -Name '" + _escape_ps(switch_name) + "' -SwitchType " + _escape_ps(st) + "; Hyper-V\\\\Get-VMSwitch -Name '" + _escape_ps(switch_name) + "' | ConvertTo-Json -Compress"
    elif action == "remove_switch":
        if not switch_name: raise ValueError("Action 'remove_switch' requires 'switch_name' parameter")
        ps_cmd = "Hyper-V\\\\Remove-VMSwitch -Name '" + _escape_ps(switch_name) + "' -Force"
    elif action == "attach_nic":
        if not name or not switch_name: raise ValueError("Action 'attach_nic' requires 'name' and 'switch_name'")
        ps_cmd = "Hyper-V\\\\Add-VMNetworkAdapter -VMName '" + _escape_ps(name) + "' -SwitchName '" + _escape_ps(switch_name) + "'; Hyper-V\\\\Get-VMNetworkAdapter -VMName '" + _escape_ps(name) + "' | ConvertTo-Json -Compress"
    elif action == "detach_nic":
        if not name: raise ValueError("Action 'detach_nic' requires 'name' parameter")
        ps_cmd = "Hyper-V\\\\Get-VMNetworkAdapter -VMName '" + _escape_ps(name) + "' | Hyper-V\\\\Remove-VMNetworkAdapter -Confirm:$false; @{success=$true; vm='" + _escape_ps(name) + "'} | ConvertTo-Json -Compress"
    elif action == "build_autounattend":
        ps_cmd = (
            "$outDir = '" + _escape_ps(out_dir) + "'; New-Item -ItemType Directory -Force -Path $outDir | Out-Null; "
            "$xmlPath = '" + _escape_ps(unattend_file) + "'; "
            "$xml = '<?xml version=''1.0'' encoding=''utf-8''?><unattend xmlns=''urn:schemas-microsoft-com:unattend''><settings pass=''windowsPE''><component name=''Microsoft-Windows-Setup'' processorArchitecture=''amd64'' publicKeyToken=''31bf3856ad364e35'' language=''neutral'' versionScope=''nonSxS''><UserData><AcceptEula>true</AcceptEula></UserData></component></settings></unattend>'; "
            "Set-Content -Path $xmlPath -Value $xml -Encoding UTF8; @{success=$true; action='build_autounattend'; path=$xmlPath} | ConvertTo-Json -Compress"
        )
    elif action == "build_autounattend_iso":
        ps_cmd = (
            "$outDir = '" + _escape_ps(out_dir) + "'; New-Item -ItemType Directory -Force -Path $outDir | Out-Null; "
            "$xmlPath = '" + _escape_ps(unattend_file) + "'; $isoPath = '" + _escape_ps(answer_iso) + "'; "
            "$xml = '<?xml version=''1.0'' encoding=''utf-8''?><unattend xmlns=''urn:schemas-microsoft-com:unattend''><settings pass=''windowsPE''><component name=''Microsoft-Windows-Setup'' processorArchitecture=''amd64'' publicKeyToken=''31bf3856ad364e35'' language=''neutral'' versionScope=''nonSxS''><UserData><AcceptEula>true</AcceptEula></UserData></component></settings></unattend>'; "
            "Set-Content -Path $xmlPath -Value $xml -Encoding UTF8; "
            "$stage = Join-Path $outDir 'iso_stage'; if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }; "
            "New-Item -ItemType Directory -Force -Path $stage | Out-Null; Copy-Item $xmlPath (Join-Path $stage 'Autounattend.xml') -Force; "
            "try { $fsi = New-Object -ComObject IMAPI2FS.MsftFileSystemImage; $fsi.FileSystemsToCreate = 3; $fsi.VolumeName = 'UNATTEND'; $fsi.Root.AddTree($stage, $true); $result = $fsi.CreateResultImage(); $stream = $result.ImageStream; $bytes = New-Object byte[] $stream.Size; [void]$stream.Read($bytes, 0, $stream.Size); [System.IO.File]::WriteAllBytes($isoPath, $bytes); @{success=$true; action='build_autounattend_iso'; xml=$xmlPath; iso=$isoPath} | ConvertTo-Json -Compress } catch { @{success=$false; action='build_autounattend_iso'; xml=$xmlPath; iso=$isoPath; error=$_.Exception.Message; hint='Autounattend.xml written; ISO build needs IMAPI2'} | ConvertTo-Json -Compress }"
        )
    elif action == "mount_os_iso":
        if not name: raise ValueError("Action 'mount_os_iso' requires 'name' (VM) parameter")
        iso = iso_path or r"D:\\Archive\\Tech\\Labs\\installers\\2022.ISO"
        ps_cmd = ("if (-not (Test-Path -LiteralPath '" + _escape_ps(iso) + "')) { throw 'OS ISO not found: " + _escape_ps(iso) + "' }; Hyper-V\\\\Get-VMDvdDrive -VMName '" + _escape_ps(name) + "' | Hyper-V\\\\Set-VMDvdDrive -Path '" + _escape_ps(iso) + "'; Hyper-V\\\\Get-VMDvdDrive -VMName '" + _escape_ps(name) + "' | Select-Object VMName, Path, ControllerNumber, ControllerLocation | ConvertTo-Json -Compress")
    elif action == "mount_answer_iso":
        if not name: raise ValueError("Action 'mount_answer_iso' requires 'name' (VM) parameter")
        aiso = answer_iso_path or answer_iso
        ps_cmd = ("Hyper-V\\\\Add-VMDvdDrive -VMName '" + _escape_ps(name) + "' -Path '" + _escape_ps(aiso) + "' -ErrorAction SilentlyContinue; Hyper-V\\\\Get-VMDvdDrive -VMName '" + _escape_ps(name) + "' | Select-Object VMName, Path, ControllerNumber, ControllerLocation | ConvertTo-Json -Compress")
    elif action == "create_template_vm":
        if not name: raise ValueError("Action 'create_template_vm' requires 'name' parameter")
        iso = iso_path or r"D:\\Archive\\Tech\\Labs\\installers\\2022.ISO"
        ps_cmd = ("$vmName = '" + _escape_ps(name) + "'; Hyper-V\\\\New-VM -Name $vmName -MemoryStartupBytes " + str(mem_bytes) + " -Generation " + str(generation))
        if switch_name: ps_cmd += " -SwitchName '" + _escape_ps(switch_name) + "'"
        vhd = vhd_path or ""
        ps_cmd += ("; if ('" + _escape_ps(vhd) + "' -ne '') { Hyper-V\\\\New-VHD -Path '" + _escape_ps(vhd) + "' -SizeBytes 42949672960 -Dynamic; Hyper-V\\\\Add-VMHardDiskDrive -VMName $vmName -Path '" + _escape_ps(vhd) + "' }; Hyper-V\\\\Get-VMDvdDrive -VMName $vmName | Hyper-V\\\\Set-VMDvdDrive -Path '" + _escape_ps(iso) + "'; Hyper-V\\\\Get-VM -Name $vmName | ConvertTo-Json -Compress")
    elif action == "list_templates":
        ps_cmd = "Hyper-V\\\\Get-VM | Where-Object { $_.Name -match 'template|tmpl|gold' -or $_.Notes -match 'template' } | Select-Object Name, State, Generation, Status | ConvertTo-Json -Compress"
    elif action == "export_template":
        if not name: raise ValueError("Action 'export_template' requires 'name' parameter")
        exp = export_path or str(Path(out_dir) / "exports")
        ps_cmd = ("New-Item -ItemType Directory -Force -Path '" + _escape_ps(exp) + "' | Out-Null; Hyper-V\\\\Export-VM -Name '" + _escape_ps(name) + "' -Path '" + _escape_ps(exp) + "'; @{success=$true; name='" + _escape_ps(name) + "'; export_path='" + _escape_ps(exp) + "'} | ConvertTo-Json -Compress")
    elif action == "start_maintenance":
        if not name: raise ValueError("Action 'start_maintenance' requires 'name' parameter")
        snap = snapshot_name or "pre_maintenance"
        ps_cmd = ("Hyper-V\\\\Checkpoint-VM -Name '" + _escape_ps(name) + "' -SnapshotName '" + _escape_ps(snap) + "'; Hyper-V\\\\Start-VM -Name '" + _escape_ps(name) + "' -PassThru | Select-Object Name, State | ConvertTo-Json -Compress")
    elif action == "stop_maintenance":
        if not name: raise ValueError("Action 'stop_maintenance' requires 'name' parameter")
        ps_cmd = "Hyper-V\\\\Stop-VM -Name '" + _escape_ps(name) + "' -Force -PassThru | Select-Object Name, State | ConvertTo-Json -Compress"
    elif action == "execute_ps":
        if not command: raise ValueError("Action 'execute_ps' requires 'command' parameter")
        ps_cmd = command
    else:
        ps_cmd = "Hyper-V\\\\Get-VM | ConvertTo-Json -Compress"

    if dry_run:
        return {"success": True, "action": action, "agent": "AGENT", "focus": FOCUS, "dry_run": True, "command": ps_cmd, "details": kwargs}

    result = _run_powershell(ps_cmd)
    result["action"] = action
    result["agent"] = "AGENT"
    result["focus"] = FOCUS
    result["command"] = ps_cmd
    return result
""")
    src = "".join(L)
    src = src.replace('"agent": "AGENT"', f'"agent": "{agent_id}"').replace('["agent"] = "AGENT"', f'["agent"] = "{agent_id}"')
    # Fix agent placeholders precisely
    src = src.replace('"agent": "AGENT"', '"agent": "%s"' % agent_id)
    src = src.replace('result["agent"] = "AGENT"', 'result["agent"] = "%s"' % agent_id)
    return src

def build_hyperv_skill_md(agent_id, tool_name, seed_intent, objectives=None, skill_id=None, focus="full"):
    import yaml
    focus = focus if focus in ACTIONS else "full"
    clean_name = (skill_id or agent_id).replace("-", " ").replace("_", " ").title()
    clean_desc = (seed_intent or "").replace('"', "").replace("\n", " ").strip()
    if len(clean_desc) > 120: clean_desc = clean_desc[:117] + "..."
    objs = "\n".join([f"- {o}" for o in (objectives or [seed_intent])])
    frontmatter_yaml = yaml.safe_dump({"name": f"{clean_name} Automation", "description": clean_desc, "tools": [tool_name]}, sort_keys=False).strip()
    docs = {
      "vm": "- `status`/`list`/`get`/`create`/`start`/`stop`/`checkpoint`/`list_checkpoints`/`restore_checkpoint`/`remove_checkpoint`/`remove`: VM + checkpoint lifecycle via Hyper-V\\\\ cmdlets\n",
      "network": "- `list_switches`/`create_switch`/`remove_switch`/`attach_nic`/`detach_nic`: switch + NIC lifecycle\n",
      "unattend": "- `build_autounattend`/`build_autounattend_iso`/`mount_os_iso`/`mount_answer_iso`/`create_template_vm`: Autounattend + ISO mount (2022.ISO)\n",
      "template": "- `list_templates`/`checkpoint_template`/`export_template`/`start_maintenance`/`stop_maintenance`: template patching\n",
      "full": ("- `status` / `list`: Inspect running virtual machines, CPU usage, assigned memory, and state\n""- `get`: Query detailed configuration for a specific virtual machine (`name`)\n""- `create`: Provision a new VM with custom RAM (`memory`), generation (`generation`), optional VHDX (`vhd_path`)\n""- `start`: Power on a virtual machine (`name`)\n""- `stop`: Shut down a virtual machine (`name`)\n""- `restart`: Reboot a virtual machine (`name`)\n""- `checkpoint` / `snapshot`: Create a Hyper-V recovery checkpoint\n""- `remove` / `delete`: Delete a virtual machine (`name`)\n""- `list_switches` / `create_switch` / `remove_switch` / `attach_nic`: Networking lifecycle\n""- `build_autounattend` / `build_autounattend_iso` / `mount_os_iso` / `create_template_vm`: Unattend/ISO templates\n""- `list_templates` / `start_maintenance` / `stop_maintenance`: Template maintenance\n"),
    }
    return f"---\n{frontmatter_yaml}\n---\n\n# {clean_name} PowerShell Automation Runbook\n\n## Purpose\n{seed_intent}\n\n## Objectives\n{objs}\n\n## Available Actions\n{docs.get(focus, docs['full'])}\n## Execution Example\n```python\n{tool_name}(action=\"status\")\n```\n"
