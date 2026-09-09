---
doc_type: ad_plan
owner_role: homelab-architect
scope: identity
last_verified: "2026-09-09"
status: active
---

# Active Directory Domain Services & Identity Hierarchy

Domain schema, Organizational Unit (OU) structure, service accounts, and group policy baseline.

## Forest & Domain Configuration
- **Forest Functional Level**: Windows Server 2022
- **Domain FQDN**: `corp.homelab.internal`
- **NetBIOS Name**: `CORP`
- **Kerberos Realm**: `CORP.HOMELAB.INTERNAL`
- **Primary Domain Controller**: `p-hl01-dc01.corp.homelab.internal` (FSMO Role Holder)
- **Replica Domain Controller**: `p-hl01-dc02.corp.homelab.internal`

## Organizational Unit (OU) Structure

```text
OU=Enterprise,DC=corp,DC=homelab,DC=internal
├── OU=Servers
│   ├── OU=DomainControllers
│   ├── OU=ApplicationServers
│   └── OU=DatabaseServers
├── OU=Workstations
│   ├── OU=AdminWorkstations
│   └── OU=DeveloperWorkstations
├── OU=ServiceAccounts
│   ├── OU=ManagedServiceAccounts (gMSA)
│   └── OU=StandardServiceAccounts
└── OU=SecurityGroups
    ├── OU=RoleBasedAccess
    └── OU=ResourceAccess
```

## Group Policy Object (GPO) Baseline
1. `GPO-DefaultDomainControllers`: Enforces NTLMv2 only (NTLMv1 disabled), Kerberos AES-256 encryption.
2. `GPO-WinRM-Hardening`: Configures HTTPS WinRM listeners on port 5986 with internal CA issued machine certs.
3. `GPO-LAPS`: Microsoft Local Administrator Password Solution automatically rotating local administrator passwords.
