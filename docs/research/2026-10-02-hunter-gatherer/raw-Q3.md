# Q3 raw notes (hunter)

## Calls (~14)
1. Read brief.json; ToolSearch to load Exa/Web tools.
2. Exa fetch anthropic.com/engineering/multi-agent-research-system (full text).
3. curl raw GitHub: open_deep_research prompts.py + deep_researcher.py; anthropic-cookbook patterns/agents/prompts/research_subagent.md (raw worked; github.com blob URL returned 403 to curl, so the repo may have moved, e.g. to anthropics/claude-cookbooks).
4. grep raw_notes / compress / summarize_webpage in ODR; curl citations_agent.md.
5. Exa fetch effective-context-engineering-for-ai-agents (2025-09-29).
6. Exa search AgentIR (arXiv 2603.04384).
7. Exa search STORM; Exa search OpenAI deep research output/annotations.
8. Exa search GPT Researcher compression; Exa search citation-accuracy benchmarks.
9. Exa fetch Claude Agent SDK subagents doc.
10. Exa search Gemini Deep Research / Interactions API.

## Leftover findings (not carded, may help the gatherer)
- Anthropic subagent prompt: hard limit of 20 tool calls / ~100 sources, stop at ~15; "Be detailed in your internal process, but more concise and information-dense in reporting the results." Also says to flag speculation ("could"/"may"), aggregators, marketing language.
- Anthropic citations_agent.md: must not modify synthesized text, only add citations; "ONLY add citations where the source documents directly support claims". Cite whole semantic units, not fragments.
- Anthropic LLM-judge rubric: factual accuracy, citation accuracy, completeness, source quality, tool efficiency, scored 0.0-1.0 plus pass/fail in a single call. Human testers found agents preferred SEO content farms over academic PDFs.
- ODR summarize_webpage: JSON {summary, key_excerpts (max 5)}, about 25-30% of original length.
- ODR compress output: "List of Queries and Tool Calls Made / Fully Comprehensive Findings / List of All Relevant Sources"; sources numbered sequentially with no gaps.
- Gemini Interactions API: UrlCitation {url,title,start_index,end_index (bytes)}; agents deep-research-preview-04-2026, deep-research-max-preview-04-2026; docs warn about malicious web pages and say to review the citations.
- DeepResearch Bench FACT: Statement-URL pairs deduped, binary support judged by Gemini-2.5-flash over Jina Reader text; metrics C.Acc and E.Cit. Gemini-2.5-Pro DR averaged 111.21 effective citations, but Perplexity DR had higher citation accuracy.
- FINDER/DEFT (arXiv 2512.01948): over 39% of failures come from content generation ("strategic content fabrication"), over 32% from retrieval (evidence integration, fact-checking).
- AgentIR: adding uncurated history hurts; the reasoning trace "implicitly curates" history. This argues for a short "why", not a full trace dump.
- STORM: rule-based source filter based on Wikipedia's reliable-sources guideline; editors flagged "source bias transfer" and "over-association of unrelated facts".

## Dead ends / gaps
- No public, explicit evidence-card JSON schema (claim/quote/url/date/why) from any production system. Vendors expose span annotations on the final text, not hunter-to-lead cards. ODR uses free-text plus a numbered source list.
- Found no empirical A/B on whether including the hunter's "why fetched" helps a curator LLM judge relevance. AgentIR is the nearest result, and it is retrieval-side.
- Did not find a "CITE" benchmark by that name. AttributionBench, CiteME, CiteEval and CiteAudit are named in arXiv 2605.06635 but not fetched.
- Google's consumer Gemini Deep Research internals (beyond the API schema) are not documented.
- No injection attempts seen in fetched pages.
