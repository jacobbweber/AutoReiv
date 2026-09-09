---
doc_type: sop_runbook
owner_role: homelab-admin
scope: identity
last_verified: "2026-09-09"
status: active
---

# SOP: Standard Operating Procedure for Joining a Node to Active Directory

Procedure for joining a Windows Server or Linux machine to the `corp.homelab.internal` domain.

## 1. Prerequisites & Name Resolution Check
- [ ] Ensure node's primary DNS resolver is set to `10.10.20.10` and secondary to `10.10.20.11`.
- [ ] Test DNS SRV query for domain controllers:
  ```powershell
  Resolve-DnsName -Name _ldap._tcp.dc._msdcs.corp.homelab.internal -Type SRV
  ```

## 2. Windows Node Domain Join
1. Execute PowerShell cmdlet from administrative console:
   ```powershell
   $Domain = "corp.homelab.internal"
   $OU = "OU=ApplicationServers,OU=Servers,OU=Enterprise,DC=corp,DC=homelab,DC=internal"
   Add-Computer -DomainName $Domain -OUPath $OU -Restart -Force
   ```

## 3. Linux Node Domain Join (SSSD / Realmd)
1. Install AD join packages:
   ```bash
   sudo apt-get update && sudo apt-get install -y realmd sssd sssd-tools adcli samba-common-bin
   ```
2. Discover and join domain:
   ```bash
   sudo realm discover corp.homelab.internal
   sudo realm join --user=svc_domain_join corp.homelab.internal --computer-ou="OU=ApplicationServers,OU=Servers,OU=Enterprise,DC=corp,DC=homelab,DC=internal"
   ```

## 4. Verification
- [ ] Verify computer account object exists in the target Active Directory OU via `Get-ADComputer`.
- [ ] Log in with domain credentials: `corp\domainadmin`.
