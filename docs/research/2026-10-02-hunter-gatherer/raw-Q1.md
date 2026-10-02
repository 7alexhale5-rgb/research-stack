# Q1 raw notes (hunter)

Queries/tools:
- Exa: "TypeSafe Jev API documentation endpoint question types pricing"; "typesafe.ai docs models pricing and limits Jev early access waitlist"; "Cloudflare Workers AI typesafe/jev model"
- curl api.typesafe.ai/ (404 {"detail":"Not Found"}, server cloudflare, x-typesafe-request-id header) and /v1/models (403 "Must supply an API key!")
- HN Algolia stories "typesafe jev" (20 hits, 2026-09-16..09-30); comments "typesafe waitlist", "jev early access", "jevtypesafeai" (none for the last)
- docs.typesafe.ai/models (Exa fetch), docs.typesafe.ai/llms.txt, docs.typesafe.ai/api.md (grep)
- PyPI / npm / crates.io / rubygems registry JSON
- jevtypesafeai.com home (WebFetch) and /terms (curl)
- typesafe.ai homepage (curl, grep for waitlist/early access)

Findings worth flagging:
- RATE LIMIT CONFLICT: official models page now says 100K tok/s / 40 req/s (= 2,400 rpm); several third-party pages (jevaiguide 2026-09-19, oflight 2026-09-19, jevtypesafeai) say 1,200 rpm / 250k tok/s. Docs say limits change without notice. Likely the docs were edited; no dated changelog found.
- ACCESS CONFLICT: typesafe.ai still says "Join Waitlist" / "early access" (fetched 2026-10-02). llmreference.com and jevtypesafeai.com claim no waitlist / self-serve since ~2026-09-20. HN comment 2026-09-19 (bjt12345, id 49766166) still complains about the waitlist. Unresolved.
- CONTEXT: 64k request / 32k state+longest question on TypeSafe direct; Cloudflare lists 32,000 tokens. Independent test: 32,204 OK, ~33,600 rejected (max_tokens_exceeded).
- PRICE: $0.042/MTok input, output free (official, OpenRouter, Vercel). apimodels.app $0.05. jevtypesafeai.com shows $0.25-$0.42/M (models page says "$0.42/M") -- 6-10x markup, or confused figure.
- jevtypesafeai.com: CODEFASHION TECH LTD, Stripe payments, contact@jevtypesafeai.com, terms dated 2026-09-21, explicitly independent, forwards requests upstream, warns production users to go direct. No AI-directed injection text seen in fetched portions. Other look-alikes mentioned: thejevai.com (cheatsheet warns it shows its own endpoint), learnjev.com, jevaiguide.com (independent guides, operators unknown).
- Versioning: aliases jev-latest, jev-preview -> jev-1.13.0; GET /v1/models lists only aliases; "jev-1.13" rejected (400) per jevaiguide even though OpenRouter slug is typesafe/jev-1.13.
- SDKs official: typesafe-sdk (PyPI 0.7.2, releases 0.0.1a0..0.7.2), @typesafe-ai/sdk (npm 0.6.0, created 2026-09-12). Third-party: Rust typesafe-jev 0.2.0 (thehumanworks/jevgrep), Ruby typesafe-jev 1.0.1 (dtheofr), Pydantic AI TypeSafeModel, LangChain TypeSafeClassifier, TanStack adapters.
- Data handling note for Q5: models page says Jev is not trained on customer requests; ZDR only for enterprise. Data processing via jevtypesafeai means a second party sees the text.

Could not find:
- Dated docs changelog showing when rate limits changed.
- Official statement on whether the waitlist is closed.
- Cloudflare's actual Jev price (dashboard only) or Cloudflare-specific rate limits.
- Any SLA/deprecation policy for pinned versions (how long jev-1.13.0 stays available).
- Did not read the HN CEO comment about output tokens (cited by learnjev) directly.
