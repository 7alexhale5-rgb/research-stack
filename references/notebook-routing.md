# NotebookLM Notebook Routing Table

## How It Works

When `--vault` is set but `--notebook` is NOT explicitly provided, the skill auto-routes to the best notebook based on keyword matching against the TOPIC. If no match is found, the skill prompts the user to create a new notebook (with a suggested category).

## Notebook Taxonomy

> **Setup:** Run `notebooklm list` to see your notebooks and their IDs. Replace `<your-id>` placeholders below with your actual notebook IDs.

| Notebook Name | Notebook ID | Domain | Keywords |
|---------------|-------------|--------|----------|
| AI Agents & Orchestration | `<your-id>` | Agent frameworks, MCP, tool use | agent, mcp, orchestration, fleet, a2a, tool-use, sdk, anthropic, claude-api, agent-sdk, swarm, crew, autogen, langgraph, langchain, function-calling, model-context-protocol |
| AI Automation & LLMs | `<your-id>` | LLM usage, prompting, AI tools | llm, gpt, gemini, claude, prompting, prompt-engineering, fine-tuning, rag, embeddings, vector, ai-tools, copilot, cursor, notebooklm, ai-coding, vibe-coding |
| CRM & Sales Systems | `<your-id>` | Sales tech, pipelines, outreach | crm, salesforce, hubspot, pipedrive, sales, pipeline, lead-gen, outreach, prospecting, cold-email, follow-up, deal, opportunity, qualification |
| Agency Operations | `<your-id>` | Running an agency, delivery, SOPs | agency, operations, fulfillment, client-management, onboarding, sop, process, workflow, project-management, retainer, scope, delivery, capacity |
| Business Strategy | `<your-id>` | Pricing, positioning, growth | pricing, positioning, strategy, business-model, scaling, growth, revenue, margin, saas, subscription, packaging, go-to-market, gtm, value-prop |
| Competitive Intelligence | `<your-id>` | Market landscape, competitors | competitor, competitive, market-landscape, alternative, comparison, benchmark, market-share, win-loss, battlecard |
| Content & Marketing | `<your-id>` | Content creation, SEO, brand | content, marketing, seo, copywriting, social-media, blog, newsletter, thought-leadership, brand, advertising, demand-gen, inbound |
| Web Development | `<your-id>` | Frontend, backend, frameworks | frontend, backend, react, nextjs, tailwind, typescript, javascript, html, css, api, rest, graphql, web-dev, ui, ux, design-system, supabase, vercel |
| Infrastructure & DevOps | `<your-id>` | Hosting, CI/CD, monitoring | devops, docker, ci-cd, deployment, vps, hosting, monitoring, linux, nginx, systemd, postgres, database, redis, ssl, dns, cloudflare |
| Personal Automation | `<your-id>` | Life automation, personal tools | personal, automation, calendar, meal-prep, training, fitness, habit, productivity, second-brain, obsidian, note-taking, pkm |
| Consulting & Client Work | `<your-id>` | Consulting frameworks, delivery | consulting, advisory, engagement, discovery, proposal, statement-of-work, sow, audit, assessment, transformation, implementation |
| Finance & Legal | `<your-id>` | Contracts, billing, compliance | finance, legal, contract, invoice, billing, tax, compliance, gdpr, privacy, terms, agreement, ip, intellectual-property |

> **Important:** Always use `notebooklm use <ID>` not `notebooklm use "<Name>"` to avoid `&` parsing issues in notebook names.

## Routing Algorithm

1. Lowercase the TOPIC
2. Tokenize into words (split on spaces, hyphens, slashes)
3. For each notebook, count keyword matches (exact + substring)
   - Exact match: word appears in keyword list → +2 points
   - Substring match: word is contained in a keyword OR keyword is contained in word → +1 point
   - Example: topic word "agents" substring-matches keyword "agent" → +1
4. Select notebook with highest point total. Resolve the `Notebook ID` from the table for use in all `notebooklm` commands.
5. Tie-breaker: prefer the notebook listed first in the table
6. If zero points across all notebooks: NO_MATCH (trigger prompt)
7. If top two notebooks are within 1 point: mention both, let user confirm

### Semantic Fallback (for zero keyword matches)

If pure keyword matching returns NO_MATCH, apply semantic inference:
- Does the topic relate to "building" or "creating" something? → Web Development or AI Agents
- Does the topic relate to "selling" or "buying"? → CRM & Sales or Business Strategy
- Does the topic mention a company name? → Competitive Intelligence or Consulting & Client Work
- Does the topic mention "how to run" or "manage"? → Agency Operations

## NO_MATCH Behavior

When no notebook matches the topic:

1. Analyze the topic to suggest a category name
2. Prompt the user:
   ```
   No existing notebook matches "{TOPIC}".
   Suggested notebook: "{SUGGESTED_NAME}"

   Options:
   a) Create "{SUGGESTED_NAME}" and continue
   b) Route to an existing notebook: [list]
   c) Skip NotebookLM for this run
   ```
3. If user picks (a): run `notebooklm create "{SUGGESTED_NAME}"`, add to routing table note
4. If user picks (b): use selected notebook
5. If user picks (c): set `--notebook` to empty, skip NB steps

## Maintaining the Table

After creating a new notebook via NO_MATCH flow:
- Add it to this routing table with appropriate keywords
- The user should periodically review this table to merge or split notebooks as domains evolve
- Target: 10-15 notebooks max. More than that dilutes the compounding effect.

## Cross-Notebook Querying (Future Enhancement)

Google now allows attaching multiple NotebookLM notebooks to a single Gemini conversation. When the skill matures, consider:
- Querying 2-3 related notebooks for cross-domain synthesis (e.g., "AI Agents" + "Business Strategy" for "AI agent pricing models")
- Using Gemini Gems to create persistent multi-notebook advisors
- This is NOT yet implemented in the routing — one notebook per run for now
