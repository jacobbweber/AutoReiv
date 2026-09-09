---
doc_type: sop_runbook
owner_role: homelab-admin
scope: compute
last_verified: "2026-09-09"
status: active
---

# SOP: Standard Operating Procedure for Expanding a Virtual Machine Disk

Hot-expansion of Hyper-V VHDX virtual hard disks and extending guest file systems.

## 1. Safety Check & Hyper-V Checkpoint Verification
- [ ] Check if the VM has active checkpoints:
  ```powershell
  Get-VMSnapshot -VMName "p-hl01-app01"
  ```
  *Note: If checkpoints exist, VHDX expansion requires checkpoint consolidation or temporary VM shutdown.*

## 2. Expand Virtual Hard Disk (VHDX) on Host
1. Run PowerShell cmdlet specifying target size (e.g. expanding to 120 GB):
   ```powershell
   Resize-VHD -Path "D:\HyperV\VirtualMachines\p-hl01-app01\Virtual Hard Disks\disk0.vhdx" -SizeBytes 120GB
   ```

## 3. Extend Guest Partition & File System
### For Windows Guest:
```powershell
# Rescan disks and extend partition to maximum available size
Update-HostStorageCache
$Partition = Get-Partition -DiskNumber 0 -PartitionNumber 2
Resize-Partition -DiskNumber 0 -PartitionNumber 2 -Size (Get-PartitionSupportedSize -DiskNumber 0 -PartitionNumber 2).SizeMax
```

### For Linux Guest (LVM / ext4):
```bash
sudo growpart /dev/sda 2
sudo pvresize /dev/sda2
sudo lvextend -l +100%FREE /dev/mapper/ubuntu--vg-ubuntu--lv
sudo resize2fs /dev/mapper/ubuntu--vg-ubuntu--lv
```

## 4. Verification
- [ ] Verify free storage with `df -h` (Linux) or `Get-Volume` (Windows).
- [ ] Update `notes/homelab/20-compute/vm_catalog.md` with new disk capacity.
