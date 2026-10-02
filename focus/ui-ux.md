# Focus lens: ui-ux (UI and UX patterns)

Use this lens before designing or reworking a screen or flow. It finds how real, shipped products
solve the same problem, with screenshots, and backs the pick with usability evidence. "Looks nice
on Dribbble" is inspiration, not evidence.

## Triggers

Suggested when the topic mentions UI, UX, onboarding, user flows, screens, layout, design
patterns, Figma, components, dashboards, checkout or usability. Bundle: none by default; pair with
`a11y`.

## Sub-question lens

1. **Pattern inventory:** how do 5 or more shipped products handle this exact flow (steps,
   fields, defaults, empty and error states)?
2. **Evidence:** what does usability research (NN/g, Baymard) say about the competing patterns,
   with the study and its date?
3. **Fit:** which pattern fits our constraints (platform, design system components, data we
   actually have), and what does it cost to build?

## Tool stack

| Tool        | Tier           | Use it for                                                               | Skip when                          |
| ----------- | -------------- | ------------------------------------------------------------------------ | ---------------------------------- |
| `mobbin`    | paid (MCP)     | Real app screens and full flows by pattern (onboarding, paywall, settings) | `--free`; web-only marketing site  |
| `refero`    | paid (MCP)     | Web app and marketing-site screens and flows                              | `--free`                           |
| `foreplay`  | paid (API)     | Landing pages and creative paired with the ads that drive to them         | product UI rather than marketing   |
| `figma`     | freemium (MCP) | Our own components, tokens and existing frames                            | no Figma file for this project     |
| `shadcn`    | free (MCP)     | Exact component APIs and registry blocks for the build                    | the project does not use shadcn    |
| `playwright`| free (MCP)     | Walk a live competitor flow and screenshot each step                      | the flow is behind a login         |
| `nngroup`   | free           | Usability research and heuristics                                         | never skip for a usability claim   |
| `baymard`   | freemium       | E-commerce and checkout benchmarks                                        | not commerce                       |
| `awwwards`  | free           | Visual direction and interaction ideas                                    | the question is about usability    |

**Free-only path:** `playwright` screenshots of 3 to 5 live competitor flows, plus `nngroup` and
`baymard` site search, plus `awwwards`/Dribbble site search for visual references, plus `shadcn`
for build fit.

## Authorities

NN/g, Baymard, Apple Human Interface Guidelines, Material Design 3 and W3C outrank design blogs.
A pattern seen in 5 shipped products is stronger evidence than one beautiful concept shot.

## Freshness

- Cache TTL: 30 days for pattern libraries, 180 days for usability research.
- Screens go stale as apps redesign; record the capture date shown by Mobbin or Refero.
- Dated trap: the default shadcn look is now widely read as "AI-made". Flag it when brand
  distinctiveness matters.

## Audit mode

With `--target <url>`: walk the target flow with `playwright`, screenshot each step, and score it
against the top 3 reference flows found in the run (step count, required fields, error handling,
empty states). Store screenshots next to the report and tag `[AUDIT:pw]`.

## Report addendum

Add a **Pattern references** section:

```text
### Pattern references
| Pattern                         | Seen in (capture date)            | Evidence                          | Source          | Recommend |
| ------------------------------- | --------------------------------- | --------------------------------- | --------------- | --------- |
| Progressive onboarding, 3 steps | app-a, app-b, app-c (2026-08)     | NN/g: fewer up-front fields helps | [MOB + NNG]     | yes       |
```

Link each reference screen or flow so the design step can open it.

## Pathway mapping

- pathway-operating-layer: `design`, plus the `ui-proof` overlay.
- development-protocol rows: `research`, `visual-spec` (reference flows feed the spec), `design`.
