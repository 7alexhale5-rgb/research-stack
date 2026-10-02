# Focus lens: legal (legal, privacy and compliance)

Use this lens when a rule, licence or regulation constrains the work. It reads the law and the
regulator, not commentary about them, and it is research, not legal advice. Flag anything
load-bearing for a qualified reviewer.

## Triggers

Suggested when the topic mentions legal, GDPR, CCPA, HIPAA, compliance, regulations, licences,
terms of service, privacy policy, contracts or the AI Act.

## Sub-question lens

1. **Which rules apply:** which statutes, regulations and licences apply, given the jurisdictions,
   data types and user types involved?
2. **What they require:** what is the exact obligation (article and section), the deadline, and
   the enforcement record?
3. **What it means for the build:** which design, data or process changes follow, and which
   questions need a lawyer?

## Tool stack

| Tool                | Tier           | Use it for                                                   | Skip when                  |
| ------------------- | -------------- | ------------------------------------------------------------ | -------------------------- |
| `legal-data-hunter` | freemium (MCP) | Statutes and case law across jurisdictions, with citations   | not connected              |
| `official-statutes` | free           | The text of the law (EUR-Lex, eCFR, legislation.gov.uk)      | never                      |
| `regulators`        | free           | Regulator guidance and enforcement decisions                 | never for an obligation    |

## Authorities

Statute and regulation text, then the regulator, then the courts, then law-firm commentary. A blog
never outranks a statute. For licences, the licence text and the SPDX entry are primary.

## Freshness

- Cache TTL: 30 days for obligations and deadlines, 7 days during a known rule-making window.
- Dated trap: phased regimes (such as the EU AI Act) have obligations that start on different
  dates. State which phase applies on which date.

## Audit mode

With `--target <repo|url>`: for a repo, list the licences of dependencies and flag copyleft
conflicts (with `deps-dev` data if the `devtools` lens is also active). For a URL, check that a
privacy policy, cookie consent and terms are present and note what data the page collects. Tag
`[AUDIT:legal]`. Never present the result as compliance sign-off.

## Report addendum

Add a **Legal authority table** section:

```text
### Legal authority table
| Obligation                      | Source (article, date in force) | Applies because              | Build impact               | Needs counsel? |
| ------------------------------- | ------------------------------- | ---------------------------- | -------------------------- | -------------- |
| Record of processing activities | GDPR Art. 30                    | EU users, personal data      | add data inventory         | no             |
```

## Pathway mapping

- pathway-operating-layer: `govern`, plus the `privacy-evidence` overlay.
- development-protocol rows: `research`, `premortem` (compliance failure modes), `ship` (gate).
