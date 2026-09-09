---
doc_type: service_catalog
owner_role: homelab-architect
scope: services
last_verified: "2026-09-09"
status: active
---

# Enterprise Homelab Public Key Infrastructure (PKI) & Certificates

Internal Certificate Authority (CA) root trust, issuance hierarchy, and certificate lifecycle tracking.

## Root CA Architecture
- **Root CA Host**: `p-hl01-ca01.corp.homelab.internal`
- **CA Common Name**: `Homelab Enterprise Root CA G1`
- **Key Algorithm / Length**: RSA 4096-bit (SHA-384 signature)
- **Validity Period**: 20 years (Expires 2046)
- **CRL Distribution Point (CDP)**: `http://pki.homelab.internal/crl/root.crl`
- **AIA / OCSP Responder**: `http://pki.homelab.internal/ocsp`

## Active Certificate Inventory

| Subject Alternative Name (SAN) | Purpose | Issued By | Expiration Date | Auto-Renewal |
| :--- | :--- | :--- | :--- | :--- |
| `*.homelab.internal` | Wildcard Internal Web Ingress | Enterprise Root CA G1 | 2028-09-01 | Certbot / ACME Internal |
| `p-hl01-dc01.corp.homelab.internal` | LDAPS & Kerberos Domain Controller | Enterprise Root CA G1 | 2027-09-01 | AD Auto-Enrollment |
| `p-hl01-dc02.corp.homelab.internal` | LDAPS & Kerberos Domain Controller | Enterprise Root CA G1 | 2027-09-01 | AD Auto-Enrollment |
| `p-hl01-hvh01.corp.homelab.internal`| Hyper-V Replica & WinRM HTTPS | Enterprise Root CA G1 | 2027-09-01 | AD Auto-Enrollment |
| `*.corp.homelab.internal` | Domain Computer Management | Enterprise Root CA G1 | 2027-09-01 | AD Auto-Enrollment |
