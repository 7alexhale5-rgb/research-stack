# Companion patches (stranded commits)

These commits were made in a cloud session on branch `claude/research-stack-refinement-tags-l7l0e3`
in each repo. Pushing failed with 403 `repo_not_connected` (the Claude GitHub App had no access), so
they never reached the remotes. Each folder holds `git format-patch origin/main..HEAD` output.

Apply in a clean checkout of the base commit:

```bash
git checkout -b claude/research-stack-refinement-tags-l7l0e3 <base>
git am docs/handoff/companion-patches/<repo>/*.patch   # path from the research-stack checkout
```

| Repo | Base (`origin/main` at export, 2026-10-02) | Patches | Tests run in the cloud session |
| --- | --- | --- | --- |
| development-protocol | `c0e2af3c6d8ac2c428a05c038351af72cfbe9ca8` | 3 | `python3 -m unittest discover tests`: 333 ran, 331 pass. The 2 failures are the root-only install tests named in its CLAUDE.md (`test_backup_and_manifest_survive_a_crash_partway_through_install`, `test_crash_midcopy_then_reinstall_and_uninstall_recovers_cleanly`); run as a normal user they should pass. `bash tests/sanitization.sh`: clean. |
| pathway-operating-layer | `4c20310a49384b131c7a1769d29cd063ffcb1554` | 4 | `python3 scripts/tests/operating_layer_test.py`: 1180 pass, 1 fail ("pathway-trust has no functional failure"). That check needs the installed guard script, which this checkout does not have (environment-only). CLAUDE.md's expected count still needs updating to the new total. |
| gravity-stack | `0d157901e09a2ce4fe1bc8f857fcbb1857381d38` | 5 | `python3 -m unittest discover -s tests -p 'test_*.py'`: 17/17. `cd site && npm run build` passed earlier in the session. |
| 1pct-moves-only | `84bd44c7cf2ae9daa2fa15d6c44e589437f327ce` | 2 | `python3 -m unittest discover tests`: 20/20. |

Commit lists:
- development-protocol: `94a3369` v3 focus lenses re-port and FOCUS_HINTS; `1630a80` ICM layout; `4fb020c` comms lens re-port (version 2.2.0).
- pathway-operating-layer: `5efa5ff` RESEARCH_FOCUS_MAP and verifier addenda; `658e4b0` derive tags from overlays and distinctive pathways; `3785d1f` `.planning` ICM room; `e4c7617` comms lens mirror.
- gravity-stack: `28ccf25` research-stack v3 docs; `59eebd2` golden source tags; `3481519` Mobbin/Refero MCP endpoints; `6a0c8b8` ICM rooms and system map; `56b6a37` comms focus tag.
- 1pct-moves-only: `5eb0ace` v3.1.0 research delegation; `8da2c7c` ignore bytecode caches.

The development-protocol port mirrors research-stack as of `32fff91` (3.1.0, comms lens and process check). If main has moved past that, re-check `skills/research-stack/references/focus/tags.json` against canonical `focus/tags.json` after applying.
