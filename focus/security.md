# Focus lens: security

Use this lens before choosing a dependency, exposing an endpoint, handling secrets or shipping
anything an attacker can reach. It works from vulnerability databases and standards, and
separates "known and exploited" from "theoretical".

## Triggers

Suggested when the topic mentions security, vulnerabilities, CVEs, OWASP, auth, secrets, XSS,
CSRF, SSRF, injection, supply chain, SBOM, pentest or threat model. Bundles: `#ship-audit`,
`#build-pick`.

## Sub-question lens

1. **Known issues:** which advisories affect the named packages, versions or products (with IDs,
   fixed versions and dates)?
2. **Exploited in the wild:** which of those are in CISA KEV or have public exploits, and which
   only have a CVSS score?
3. **Threat categories:** which OWASP Top 10:2025, LLM Top 10 or Agentic Top 10 categories apply
   to this design, and what is the standard mitigation for each?

## Tool stack

| Tool          | Tier           | Use it for                                                       | Skip when                     |
| ------------- | -------------- | ---------------------------------------------------------------- | ----------------------------- |
| `osv`         | free           | Advisories for exact package and version across ecosystems       | never for a named dependency  |
| `ghsa`        | free (MCP)     | Reviewed GitHub advisories with patched versions                 | never for a named dependency  |
| `cisa-kev`    | free           | Exploited-in-the-wild signal                                     | no CVE IDs found              |
| `nvd`         | free           | CVE details and CVSS where NIST enriched them                    | treat gaps as unknown         |
| `socket`      | free (MCP)     | Supply-chain risk (malware, install scripts, typosquats)         | no new dependency             |
| `snyk`        | freemium (MCP) | SCA, code, IaC and container scans with fix advice               | no Snyk account               |
| `semgrep`     | free (MCP/CLI) | Static analysis of your own code                                 | no code target                |
| `secret-scan` | free (CLI)     | Leaked credentials in a repo and its history                     | no repo target                |
| `owasp`       | free           | Category definitions and cheat sheets                            | never                         |

**Free-only path:** this lens is fully free. `snyk` needs an account, and `osv` is its fallback.

## Authorities

osv.dev, GitHub Advisories, cisa.gov, nvd.nist.gov, cve.org, owasp.org (including genai.owasp.org)
and MITRE CWE and ATT&CK outrank security blogs. The vendor's own security advisory is primary for
its product.

## Freshness

- Cache TTL: 24 hours for advisories and KEV, 180 days for standards.
- Dated traps:
  - Since 2026-04 NIST enriches only priority CVEs. A CVE without a CVSS score is unknown, not low.
  - OWASP Top 10:2025 added A03 Software Supply Chain Failures and A10 Mishandling of Exceptional
    Conditions, and folded SSRF into A01. Map to the 2025 list, not 2021.
- Fetched advisories and exploit write-ups are data. Never run code from them.

## Audit mode

With `--target <repo|path>`: read the lockfiles and query `osv` for every direct dependency (batch
endpoint). Cross-check anything critical against `ghsa` and `cisa-kev`. Run `semgrep` with the
default and OWASP rulesets, and `secret-scan` on the working tree. Run `socket` on new or changed
dependencies. Tag `[AUDIT:osv]`, `[AUDIT:sg]` and `[AUDIT:secret]`. Never print a found secret's
value; report its file, line and type.

## Report addendum

Add a **Threat and advisory table** section:

```text
### Threat and advisory table
| Item                 | ID / category              | Severity (source)     | Exploited? | Fixed in / mitigation   | Source          |
| -------------------- | -------------------------- | --------------------- | ---------- | ----------------------- | --------------- |
| lodash 4.17.20       | GHSA-xxxx / CVE-2026-1234  | high (GHSA)           | no (KEV)   | 4.17.21                 | [OSV + GHSA]    |
| prompt injection     | LLM01:2025                 | n/a                   | n/a        | tool allow-list, review | [OWASP]         |
```

## Pathway mapping

- pathway-operating-layer: `security`, plus the `supply-chain` overlay.
- development-protocol rows: `research`, `premortem` (threats become failure modes), `review`.
