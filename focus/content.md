# Focus lens: content (content, ads and creative)

Use this lens when the work produces or competes on content: landing copy, blog and newsletter
strategy, ad creative, hooks, short-form video. It studies what is running and working in the
market now, not what a listicle says works.

## Triggers

Suggested when the topic mentions content, copywriting, blog, newsletter, ad creative, ads, hooks,
social posts, short-form, video, campaign or landing copy. Bundles: `#launch`, `#competitive`.

## Sub-question lens

1. **What is running:** which ads, hooks and formats are competitors running now, and for how long
   (longevity is a proxy for performance)?
2. **What resonates:** which angles, offers and formats get engagement or citations in this niche,
   with numbers?
3. **Gaps:** which questions does the audience ask that nobody answers well (search demand,
   community threads, AI answers)?

## Tool stack

| Tool              | Tier          | Use it for                                                           | Skip when                         |
| ----------------- | ------------- | -------------------------------------------------------------------- | --------------------------------- |
| `foreplay`        | paid (API)    | Competitor ad libraries, saved swipe files, brand spy across platforms | `--free`; no competitor or brand |
| `meta-ad-library` | free          | Live ads per advertiser on Meta, with start dates                     | the niche does not advertise on Meta |
| `spyfu`           | paid (API)    | Years of competitor Google Ads copy and keyword spend                  | `--free`                          |
| `dataforseo`      | paid (MCP)    | Content gap: questions and keywords with volume                       | `--free`                          |
| `hubspot`         | internal      | Your own content analytics and campaign attribution                   | no HubSpot portal for this brand  |
| `higgsfield`      | internal      | Virality prediction and analysis for a short-form video               | no video asset in scope           |
| `youtube`         | free          | Transcripts of top-performing videos in the niche                     | no video angle                    |

**Free-only path:** `meta-ad-library` + web search for the competitor's landing pages + community
search (`site:reddit.com`, HN) for audience questions + `youtube` transcripts. Ad longevity from the
library's start dates stands in for performance data.

## Authorities

Platform documentation (Meta transparency centre, TikTok Creative Center, YouTube Help, Think with
Google) outranks agency blogs. Your own analytics outrank both for "what works for us" questions.

## Freshness

- Cache TTL: 7 days for ad libraries, 30 days for format guidance.
- Ads rotate weekly; always record the date range seen.
- Dated trap: ad-library coverage differs by region and ad category. Say which region was searched.

## Audit mode

With `--target <url>`: fetch the page and extract the headline, sub-head, primary CTA, proof
elements and reading level. Compare each against the 3 strongest competitor pages found in the
run. With `foreplay` or `meta-ad-library`, list the target brand's own running ads. Tag
`[AUDIT:copy]`.

## Report addendum

Add a **Content and creative angles** section:

```text
### Content and creative angles
| Angle / hook                     | Who runs it (since)          | Evidence of traction          | Source      | Use it? |
| -------------------------------- | ---------------------------- | ----------------------------- | ----------- | ------- |
| "Cut onboarding to 5 minutes"    | competitor-a (2026-06-02)    | running 120+ days, 14 variants | [FP]        | test    |
```

## Pathway mapping

- pathway-operating-layer: `docs`, `release`.
- development-protocol rows: `research`, `spec` (messaging requirements), `ship` (launch assets).
