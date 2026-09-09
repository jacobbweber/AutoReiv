---
doc_type: sop_runbook
owner_role: homelab-admin
scope: operations
last_verified: "2026-09-09"
status: active
---

# SOP: Standard Operating Procedure for Provisioning a New Virtual Machine

Step-by-step procedure for deploying and configuring a new virtual machine on the Hyper-V hypervisor.

## 1. Prerequisites & Validation Checks
- [ ] Consult `notes/homelab/10-network/vlan_matrix.md` and select target VLAN and subnet.
- [ ] Consult `notes/homelab/10-network/ipam_allocations.md` and reserve an unassigned static IP.
- [ ] Verify host `p-hl01-hvh01` has sufficient storage on `D:\HyperV\VirtualMachines` via `lookup-host-spec`.
- [ ] Select VM sizing tier from `notes/homelab/00-governance/sizing_tiers.md`.

## 2. Declarative Execution (OpenTofu / IaC)
1. In the IaC repository `infra/tofu/vms/`, create or update the resource block:
   ```hcl
   module "guest_vm" {
     source       = "../modules/hyperv-vm"
     vm_name      = "p-hl01-app02"
     generation   = 2
     vcpus        = 4
     memory_mb    = 8192
     vswitch_name = "vSwitch-External"
     vlan_id      = 30
     os_disk_gb   = 80
     template_vhd = "E:/HyperV/Templates/tmpl-ubuntu2404-server.vhdx"
   }
   ```
2. Execute validation:
   ```bash
   tofu plan -out=vm.plan
   ```
3. Request review and apply:
   ```bash
   tofu apply vm.plan
   ```

## 3. Post-Provisioning Verification
- [ ] Verify VM state is `Running` in Hyper-V: `Get-VM -Name "p-hl01-app02" | Select-Object State, Uptime`
- [ ] Verify network connectivity: `Test-Connection -ComputerName 10.10.30.52 -Count 3`
- [ ] Record newly provisioned VM in `notes/homelab/20-compute/vm_catalog.md`.
