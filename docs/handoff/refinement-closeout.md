# Refinement closeout (cloud session, 2026-10-02)

The cloud session that ran the research-stack v3 refinement is done. This file marks the handoff.

## Finished and on a remote

- **research-stack**: v3, focus lenses, registry, validator, `comms` lens (3.1.0), process check. PR #2 merged (with #3) into `main` at `786dc2a`.
- **consultops-live** (PrettyFlyForAI), both draft PRs green and waiting on the owner:
  - **#785** `claude/dialer-ringcentral-research`, head `88a9939`: dialer dossier, Phase 1 SPEC, ARCHITECTURE, visual pack, acceptance tests (kept in `.planning/.../acceptance/`). It carries #786's commit and a one-line `knip.json` ignore for `.planning/**`.
  - **#786** `claude/deps-audit-fix`, head `054dc31`: clears `npm audit` on `main`. It bumps hono, overrides basic-ftp to ^6.2.1, removes the Lighthouse CI leftovers (from #632), and moves promptfoo to a `--no-save` install. Merge #786 before #785. #632 and #782 then become redundant.

## Not on a remote (exported here)

- The four companion repos' commits: see [companion-patches/README.md](companion-patches/README.md). Nothing else in the container is unpushed. All working trees are clean.

## Left to do

1. Apply the companion patches, run each repo's tests, and open PRs. Link them from research-stack. Update pathway-operating-layer's expected test count in its CLAUDE.md.
2. Check the development-protocol port against research-stack `main` (#3 may have changed lenses after `32fff91`) and re-port per its `docs/PORTING.md` if needed. Re-record the `sync/sources.lock.json` hashes.
3. Owner decisions still open:
   - **pathway-operating-layer focus tags:** derive them from goal keywords. Today `comms` is derived only from security-type items. A yes/no is pending.
   - **consultops #785 review ledger:** the 18 screens and 11 diagrams need a correct/wrong verdict each.
   - **Meeting booked:** should it move the lead to Qualified or only to Contacted?
   - **Inbound calls:** should they count as contact?
   - **Meeting field:** is a date-only field enough?
4. **promptfoo install step not yet exercised.** The `npm run promptfoo:install` step in consultops `promptfoo.yml` has not run in CI, because that job is gated off by `PROMPTFOO_ENABLED`. The `ci.yml` install step did run and pass.

## Uncertain

- The pathway-trust check failing in pathway-operating-layer is believed to be environment-only: the installed guard script is absent in the clone. Confirm locally.
- consultops `audit-receipt.test.mjs` › "timeout kills a detached-pipe descendant" failed in the container on untouched `main` too. CI passed it, so it is treated as container-specific.
