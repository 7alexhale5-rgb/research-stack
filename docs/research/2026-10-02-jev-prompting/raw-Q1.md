# Q1 raw notes (hunter)
Sources fetched with curl as .md from docs.typesafe.ai (llms.txt and sitemap.xml list them all). Page copies stayed in the session scratchpad (not published: full vendor pages).
Pages: primitives, primitives/{choice,score,noul,advanced}, model-jaggedness/jev-1.13 (reviewed 2026-09-17), agent-skill, api.md, concepts/how-to-build-with-system-one, patterns/fan-out, confidence, cookbooks/parallel_questions.
Official agent skill: raw.githubusercontent.com/typesafe-ai/skills/main/skills/typesafe-ai/SKILL.md. The gh API is blocked for the typesafe-ai org, so I did not list the repo tree or its reference files.

## Extra verbatim guidance worth keeping
- Primitives: "Question IDs are for your code. They are not sent to the model. Write the complete question in `instructions`, even when the ID seems self-explanatory."
- Primitives: "When a question is about one of those parts, name it in the `instructions` with a dot-and-index path to its key, including the backticks."
- Score: "Low confidence on a Score usually means one of three things. The levels overlap for this state, the question is measuring more than one thing, or the state doesn't say enough to place it."
- Score: "If the top of your scale has a rare extreme case you need to act on differently, give it its own level."
- Score: "If there is no in-between at all ... use a Choice instead, or split the question into several Noul questions. ... Two wordings of the same scale can behave differently on your data."
- Score, numbers-only levels: with numeric levels the model "has nothing to match against and splits the probability between 0 and 1".
- Score example levels (bug_severity): 'Cosmetic; no impact to functionality' / 'Broken or degraded feature, but workaround exists' / 'Blocking issue; no workaround exists'.
- Noul: "Phrase the question so that a high value means yes. ... 'Is the message free of personal data?' inverts the meaning". "Make the boundary between yes and no unambiguous. 'Does this candidate have any Python experience?' works well because 'any' leaves no middle ground."
- Noul criteria shape: {true: 'Mentions a prior attempt, ticket, or that they have asked before', false: 'No sign of any previous contact'}.
- Jaggedness: "Aim for instructions which are easy for the average person to read and understand." "treat the criteria as an extension of the instruction." For dates, use a Choice with an explicit "not stated" option.
- Jaggedness reminder list: avoid "Asking the model something code can compute exactly", "Hiding several judgments inside one question", "System Two tasks", "Giving it more context in `state` than the question needs. Jev suffers from context rot".
- How-to-build: "Ask the most explicit, narrow, specific, atomic questions you can." "Keep questions short."
- Agent-skill page: "Agents aren't great at writing questions, so expect to edit collaboratively with them."
- SKILL.md: "State each speculative premise explicitly" (the fan-out example uses 'If this is a shipping problem, which kind is it?').
- API: max 255 Choice options; Score 2-10 levels.
- Confidence: low Choice confidence "often means none of the options are a clear winner"; low Score confidence "often means the levels are ambiguous, multi-dimensional, or the state doesn't contain enough to go on".

## Third-party (Exa search), all unaffiliated
learnjev.com, jev-tutorial.org, thejevai.com, jevdirectory.org, lmspedia.org, befailproof.ai. These mostly restate the official docs. Only lmspedia has its own number (73.3% agreement, n=15), carded as low. learnjev.com claims a "two-stage sampler" above 255 options, which I could not verify and did not card.

## Dead ends / not found
- I did not look for a separate /guides, /best-practices or /prompting page; the sitemap has none, and guidance lives on the primitive pages.
- I did not check typesafe.ai/blog, PyPI/npm READMEs, the changelog or the Cloudflare page; I ran out of budget.
