# Hunter/gatherer closeout

Closeout from the cloud session `session_01VgGWytmF5iJ5ACGBmuaA4S` (2026-10-02), so the local
session can take over research-stack. Written after PR #2 (v3) and PR #3 (hunter/gatherer)
merged into `main` at `786dc2a`.

## Finished and merged (PR #3)

- **Hunter/gatherer mode**, SKILL.md Step 3H. It is on by default for `--deep` and for runs
  with 4+ sub-questions; `--hunt` / `--no-hunt` override. The protocol is in
  `references/hunter-gatherer.md`.
- **`scripts/gather.py`**, standard library only: `rubric` (`--variant structured|plain`),
  `prompt` (the free Claude-subagent scorer), `score --scorer jev` (TypeSafe direct, pinned
  `jev-1.13.0`, or `--host cloudflare`), `merge`, `check`, `route`
  (keep/drop/requote/escalate/flagged plus coverage and re-hunt), `agree` (Cohen's kappa) and
  `eval` (keep and drop precision against the lead's labels per threshold). Tested in
  `tests/test_gather.py`, with fixtures `tests/fixtures/gather-*`; the full suite was 104 OK at
  merge.
- **A Jev-ready rubric** that follows TypeSafe's rules. The guide is
  `references/jev-question-design.md`:
  - Six questions: `subq`, `specific`, `impact` and `supported` are asked of Jev; `authority` is
    set in code and `injection` by a Claude pass.
  - Jev's state is `claim` plus `quote` only.
  - Score answers are routed on their probability distribution, never the fractional score.
  - Confidence gates only for Jev.
- **Registry** entries `jev` (paid, shadow mode) and `claude-subagent` (94 tools); a `Gatherer:`
  dashboard line; docs, CI and the installer.
- **Two dogfood dossiers with every artifact:**
  - `docs/research/2026-10-02-hunter-gatherer-jev-dossier.md` (+ folder): 70 cards, two
    scorers, lead labels, skeptic.
  - `docs/research/2026-10-02-jev-prompting-dossier.md` (+ folder): 48 cards, v1 and v2
    re-scores, and a strict-card re-hunt (2/16 to 16/16 cards fully backed by their quotes).
- **Labels:** 118 keep/drop labels in the two `labels.jsonl` files. About 200 are needed before
  any threshold is tuned.

## Left to do

1. **Jev A/B.** It needs `TYPESAFE_API_KEY` set as an environment variable in the environment
   settings, never pasted into chat. Then, per run folder:
   - `gather.py score <brief> <cards...> --scorer jev --variant structured --out jev-s.jsonl`,
     and the same with `--variant plain --out jev-p.jsonl`.
   - `gather.py merge jev-s.jsonl scores-sonnet-v2.jsonl --questions injection --out m-s.jsonl`,
     and the same for the plain run.
   - `gather.py eval m-s.jsonl labels.jsonl <cards...>` and the same for the plain run.
   - Jev stays in shadow mode until it matches Claude's agreement with the lead labels on about
     200 in-domain cards.
2. **TypeSafe benchmark-publishing check.** An unverified hunter note (raw-Q2.md in the first
   dossier folder) says TypeSafe's Master Customer Agreement §2.3(f) restricts publishing
   benchmarks. Read the MCA before committing any Jev numbers to this public repo.
3. **development-protocol re-port.** Its `skills/research-stack/` port has neither
   hunter/gatherer mode nor `gather.py` nor the new references. `scripts/CONTEXT.md` rule 5
   requires the re-port. I did not touch development-protocol.
4. **CITE-AI re-source.** SKILL.md (from v3) cites "CITE-AI" (existence F1 0.81 against
   attributable F1 0.62). A hunter could not find a study by that name; arXiv 2605.06635 names
   AttributionBench, CiteME, CiteEval and CiteAudit instead. Re-source or remove the citation.
5. **Smaller follow-ups** named in the dossiers:
   - seed known-bad cards in the next run to test the drop path;
   - apply the strict card rules to all sub-questions and re-measure;
   - check whether Claude-scorer precision under v2 recovers once cards are strict;
   - treat upstream retention behind Cloudflare's zero-data-retention flag as unverified.

## Unpushed or uncertain state

- **Nothing unpushed in any repo.** research-stack, development-protocol, gravity-stack,
  pathway-operating-layer, 1pct-moves-only and consultops-live were all clean, with no local
  commits, on 2026-10-02. Only research-stack was changed. No patches were needed.
- **Kept out of the repo on purpose:** these stayed in this session's scratchpad and will be
  lost when it is archived. All are reproducible.
  - Full TypeSafe doc page copies and a 30 KB quote-by-quote rulebook. These are vendor text;
    the guide paraphrases them with short quotes.
  - Hunters' helper scripts.
  - My first chat-only verdict report, which the first dossier supersedes.
- **This branch** was reset to `main` (`786dc2a`) after the merge, because it held only merged
  history, and this file was added on top. There is no PR for this commit, as asked.
- **Jev was never called.** Every Jev claim in the guide comes from TypeSafe's docs or
  third-party tests, not from a run of our own.
