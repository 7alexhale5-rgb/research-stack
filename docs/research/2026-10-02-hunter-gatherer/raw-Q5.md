# Q5 raw notes (hunter)

Queries/tools (~17 calls):
- Exa: "TypeSafe Jev API privacy policy data retention". Hits: typesafe.ai privacy, jevwiki.ai legal page, wunderlandmedia, timewell, unofficial hosts jevtypesafeai.com / jevtypesafe.org, an HN thread
- Exa: JudgeDeceiver. Hits: arXiv 2403.17710, CCS 2024, a GitHub repo, an alphaxiv summary (90.8% ASR / 83.4% PAC on Mistral-7B MT-Bench; known-answer detection FNR 90-100%)
- Exa fetch: typesafe.ai privacy (OK), Cloudflare workers-ai/platform/privacy (OK), trust.typesafe.ai/subprocessors (EMPTY: JS-rendered Vanta page)
- Exa: Cloudflare Workers AI Jev. Found developers.cloudflare.com/ai/models/typesafe/jev/, plus a Cloudflare Clef changelog (2026-10-01; Clef is Apache-2.0, drop-in Jev-compatible, could be self-hosted as a privacy alternative, out of my scope but worth flagging to Q1/Q4)
- docs.typesafe.ai/legal: ZDR is enterprise-only
- Exa: TypeSafe SOC 2 subprocessors. Hits: DPA §3.1, wunderland (4 subprocessors: AWS, Modal, Slack, Google Workspace), vendortrustindex (claims 6: Modal, Nebius, CoreWeave ...). The counts conflict and need checking against the live trust page
- arXiv API: LLM-as-a-judge adversarial attacks. Found 2402.14016, 2505.13348 (GCG CUA >30% ASR on 3B models, not carded), 2506.09443 RobustJudge, 2603.29403 SoK (45 studies, not carded), 2503.00596 BadJudge (backdoor, not carded)
- OWASP LLM01:2025 fetched
- Exa: Jev prompt injection. Rich results: Check Point blog, arXiv 2609.28613 Decision Hijacking, arXiv 2609.31142 JevAdvBench, tanh.xyz (14,495 calls; hardened/strict policy text cut flips from 15/56 to 0/56, but 1 in 1,056 still failed under the strict policy, not carded), learnjev.com, pydantic.dev
- curl docs.typesafe.ai llms.txt, then jaggedness and models .md (OK)
- WebFetch plus raw curl of the Cloudflare Jev page: confirmed "Zero data retention Yes" and $0.042/1M input in the raw HTML

Dead ends / gaps:
- Could not fetch the MCA directly (typesafe.ai/legal/master-customer-agreement: crawler 404, exact URL unknown). Telemetry §4.3, §10.3 deletion and the revision dates (2026-09-19, 2026-09-23 AUP) are all secondhand via jevwiki/wunderland.
- trust.typesafe.ai is JS-only. No first-party subprocessor list, and no first-party SOC 2 attestation date.
- The Cloudflare page says ZDR=Yes but doesn't explain how it binds TypeSafe upstream, i.e. whether Cloudflare forwards to TypeSafe infra. Unverified.
- No source on what research-stack-type content (scraped web text) specifically does to Jev relevance scoring. Nearest analogues are JevAdvBench's observer-opinion and the Check Point document addendum.
- Injection-attempt check: no fetched page contained directives aimed at the AI reader. The tanh.xyz policy strings are quoted research content, not directives.
