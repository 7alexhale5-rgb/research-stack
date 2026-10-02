#!/usr/bin/env python3
"""Lint and query the research-stack focus lenses. Python 3.9+ standard library only.

Usage:
  focus_check.py lint                 check tags.json, every focus/<tag>.md and the tool registry
  focus_check.py suggest "<topic>"    print the focus tags whose triggers match the topic
  focus_check.py plan <tag|#bundle>...  print the tool plan (registry rows) for the given tags
  focus_check.py probe [tag|#bundle]... report which keys and CLIs are present (never values);
                                      MCP tools are listed by prefix for the agent to match
  focus_check.py table                print the registry as a markdown table (docs/tools-reference.md)
  focus_check.py docs                 fail if docs/tools-reference.md is out of sync with the registry

Exit 0 on success, 1 on a lint failure or unknown tag, 2 on a usage error. Read-only.
"""

import argparse
import json
import os
import re
import shutil
import sys

sys.dont_write_bytecode = True  # lint imports validate_report; keep installs free of __pycache__

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Mirrors pathway-operating-layer (scripts/operating-layer.py: PATHWAY_CANON_ORDER and
# RISK_OVERLAYS) and development-protocol (devproto.py checklist rows). If those change,
# change these and the lint will show every lens that needs a new mapping.
KNOWN_PATHWAYS = [
    "govern", "research", "data", "security", "design", "implementation",
    "quality", "field", "observability", "techdebt", "release", "docs",
]
KNOWN_OVERLAYS = [
    "tenant-authz", "privacy-evidence", "production-mutation", "rollback", "supply-chain",
    "incident-response", "ui-proof", "llm-agent-eval", "human-gate",
]
DEVPROTO_ROWS = [
    "pathway", "brainstorm", "research", "spec", "planning", "visual-spec", "design",
    "premortem", "audit-setup", "build", "verify", "review", "simplify", "commit", "ship",
    "compound", "closeout",
]
LENS_HEADINGS = [
    "Triggers",
    "Sub-question lens",
    "Tool stack",
    "Authorities",
    "Freshness",
    "Audit mode",
    "Report addendum",
    "Pathway mapping",
]
TAG_FIELDS = ["title", "addendum", "triggers", "source_tags", "authorities",
              "pathways", "overlays", "devproto_rows"]
REGISTRY_FIELDS = ["id", "name", "kind", "cost", "best_at", "focus", "source_tag", "detect", "docs"]
KINDS = {"mcp", "api", "cli", "builtin", "connector"}
COSTS = {"free", "freemium", "paid", "internal"}
DOCS_BEGIN = "<!-- registry:begin -->"
DOCS_END = "<!-- registry:end -->"
ID_CELL_RE = re.compile(r"^\|\s*`([a-z0-9][a-z0-9-]*)`")


def paths(root=ROOT):
    """Standalone layout first (focus/, references/), then the ported one (references/focus/)."""
    for focus_dir in (os.path.join(root, "focus"), os.path.join(root, "references", "focus")):
        if os.path.isfile(os.path.join(focus_dir, "tags.json")):
            return {
                "focus": focus_dir,
                "manifest": os.path.join(focus_dir, "tags.json"),
                "registry": os.path.join(root, "references", "tool-registry.json"),
                "docs": os.path.join(root, "docs", "tools-reference.md"),
            }
    raise FileNotFoundError(f"no focus/tags.json under {root}")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sections(text):
    """Map '## Heading' -> body text."""
    out, current, buf = {}, None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                out[current] = "\n".join(buf)
            current, buf = line[3:].strip(), []
        elif current is not None:
            buf.append(line)
    if current is not None:
        out[current] = "\n".join(buf)
    return out


def lens_tool_ids(text):
    body = sections(text).get("Tool stack", "")
    return [m.group(1) for m in (ID_CELL_RE.match(l) for l in body.splitlines()) if m]


def expand(names, manifest):
    """Resolve tags and #bundles. Returns (tags, unknown)."""
    tags, unknown = [], []
    for raw in names:
        for part in raw.split(","):
            name = part.strip().lstrip("#").lower()
            if not name:
                continue
            members = manifest["bundles"].get(name, [name])
            for t in members:
                if t not in manifest["tags"]:
                    unknown.append(t)
                elif t not in tags:
                    tags.append(t)
    return tags, unknown


def suggest(topic, manifest):
    hits = []
    for tag, lens in manifest["tags"].items():
        found = sorted({m.group(0).lower() for m in re.finditer(lens["triggers"], topic, re.I)})
        if found:
            hits.append((tag, found))
    hits.sort(key=lambda h: -len(h[1]))
    return hits[: manifest.get("limits", {}).get("max_tags", 4)]


def lint(root=ROOT):
    p = paths(root)
    manifest, registry = load(p["manifest"]), load(p["registry"])
    errors = []
    tags = manifest.get("tags", {})
    if not tags:
        errors.append("tags.json: no tags")
    # Source tags the validator knows, so lens tags never collide with base tags silently.
    sys.path.insert(0, os.path.join(root, "scripts"))
    try:
        import validate_report  # noqa: WPS433 (local import keeps lint usable alone)
        base_tags = set(validate_report.TAGS)
    except ImportError:
        base_tags = set()
    finally:
        sys.path.pop(0)

    for tag, lens in tags.items():
        where = f"tags.json[{tag}]"
        for field in TAG_FIELDS:
            if field not in lens:
                errors.append(f"{where}: missing '{field}'")
        try:
            re.compile(lens.get("triggers", ""))
        except re.error as e:
            errors.append(f"{where}: triggers do not compile ({e})")
        for pw in lens.get("pathways", []):
            if pw not in KNOWN_PATHWAYS:
                errors.append(f"{where}: unknown pathway '{pw}'")
        for ov in lens.get("overlays", []):
            if ov not in KNOWN_OVERLAYS:
                errors.append(f"{where}: unknown overlay '{ov}'")
        for row in lens.get("devproto_rows", []):
            if row not in DEVPROTO_ROWS:
                errors.append(f"{where}: unknown development-protocol row '{row}'")
        if "research" not in lens.get("devproto_rows", []):
            errors.append(f"{where}: devproto_rows must include 'research'")
        if not lens.get("source_tags"):
            errors.append(f"{where}: no source_tags")

        md = os.path.join(p["focus"], f"{tag}.md")
        if not os.path.isfile(md):
            errors.append(f"{tag}.md: missing lens file")
            continue
        with open(md, encoding="utf-8") as f:
            text = f.read()
        secs = sections(text)
        for heading in LENS_HEADINGS:
            if heading not in secs:
                errors.append(f"{tag}.md: missing '## {heading}'")
        if lens.get("addendum") and lens["addendum"].lower() not in secs.get("Report addendum", "").lower():
            errors.append(f"{tag}.md: 'Report addendum' must name '{lens['addendum']}'")
        ids = lens_tool_ids(text)
        if not ids:
            errors.append(f"{tag}.md: 'Tool stack' table lists no registry ids")
        for tid in ids:
            entry = registry.get(tid)
            if entry is None:
                errors.append(f"{tag}.md: tool '{tid}' is not in tool-registry.json")
            elif tag not in entry.get("focus", []):
                errors.append(f"{tag}.md: tool '{tid}' lists focus {entry.get('focus')} without '{tag}'")
        for tid, entry in registry.items():
            if tag in entry.get("focus", []) and tid not in ids:
                errors.append(f"{tag}.md: registry tool '{tid}' claims '{tag}' but is not in the lens")

    for name, members in manifest.get("bundles", {}).items():
        if name in tags:
            errors.append(f"bundle '{name}' shadows a tag")
        for m in members:
            if m not in tags:
                errors.append(f"bundle '{name}': unknown tag '{m}'")

    for tid, entry in registry.items():
        where = f"tool-registry.json[{tid}]"
        if entry.get("id") != tid:
            errors.append(f"{where}: id field must equal its key")
        for field in REGISTRY_FIELDS:
            if field not in entry:
                errors.append(f"{where}: missing '{field}'")
        if entry.get("kind") not in KINDS:
            errors.append(f"{where}: kind must be one of {sorted(KINDS)}")
        if entry.get("cost") not in COSTS:
            errors.append(f"{where}: cost must be one of {sorted(COSTS)}")
        for t in entry.get("focus", []):
            if t != "base" and t not in tags:
                errors.append(f"{where}: unknown focus '{t}'")
        fb = entry.get("fallback")
        if fb and fb not in registry:
            errors.append(f"{where}: fallback '{fb}' is not in the registry")
        st = entry.get("source_tag")
        known_tags = base_tags | {s for lens in tags.values() for s in lens.get("source_tags", [])}
        if st and known_tags and st not in known_tags:
            errors.append(f"{where}: source_tag '{st}' is unknown to the validator")
        if entry.get("cost") == "paid" and not entry.get("fallback"):
            errors.append(f"{where}: a paid tool needs a free fallback")
    return errors


def table(registry):
    rows = [
        "| Tool | Kind | Cost | Tag | Focus | Best at | Fallback |",
        "| ---- | ---- | ---- | --- | ----- | ------- | -------- |",
    ]
    for tid in sorted(registry, key=lambda k: (registry[k]["focus"][0], k)):
        e = registry[tid]
        rows.append(
            f"| [{e['name']}]({e['docs']}) `{tid}` | {e['kind']} | {e['cost']} | "
            f"`[{e['source_tag']}]` | {', '.join(e['focus'])} | {e['best_at']} | "
            f"{('`' + e['fallback'] + '`') if e.get('fallback') else '-'} |"
        )
    return "\n".join(rows)


def docs_in_sync(p, registry):
    with open(p["docs"], encoding="utf-8") as f:
        text = f.read()
    if DOCS_BEGIN not in text or DOCS_END not in text:
        return False, "docs/tools-reference.md has no registry markers"
    current = text.split(DOCS_BEGIN, 1)[1].split(DOCS_END, 1)[0].strip()
    if current != table(registry).strip():
        return False, "docs/tools-reference.md registry table is stale: run `focus_check.py table`"
    return True, "docs in sync"


def plan(tags, manifest, registry):
    lines = []
    for tag in tags:
        lens = manifest["tags"][tag]
        lines.append(f"{tag}: {lens['title']} -> addendum '{lens['addendum']}'")
        with open(os.path.join(paths()["focus"], f"{tag}.md"), encoding="utf-8") as f:
            ids = lens_tool_ids(f.read())
        for tid in ids:
            e = registry[tid]
            fb = f" (fallback: {e['fallback']})" if e.get("fallback") else ""
            lines.append(f"  - [{e['source_tag']}] {e['name']} [{e['kind']}, {e['cost']}]{fb}")
    return "\n".join(lines)


def probe(tags, registry, free=False):
    """Availability by key and CLI. MCP and connector tools cannot be seen from a script:
    their prefixes are printed so the agent can match them against its own tool list."""
    wanted = set(tags) | {"base"}
    lines = []
    for tid in sorted(registry):
        e = registry[tid]
        if not wanted.intersection(e["focus"]):
            continue
        det = e["detect"]
        if free and e["cost"] == "paid":
            state = "skipped (--free)"
        else:
            env_ok = [k for k in det.get("env", []) if os.environ.get(k)]
            cli_ok = [c for c in det.get("cli", []) if shutil.which(os.path.expanduser(c)) or os.path.isfile(os.path.expanduser(c))]
            if det.get("env") and env_ok:
                state = f"key set ({', '.join(env_ok)})"
            elif det.get("env_optional"):
                state = "available (keyless; a key raises the quota)"
            elif cli_ok:
                state = f"cli ok ({', '.join(cli_ok)})"
            elif det.get("mcp"):
                state = "check tool list for " + " | ".join(det["mcp"])
            elif det.get("env") or det.get("cli"):
                state = "missing"
                if e.get("fallback"):
                    state += f" -> fallback {e['fallback']}"
            else:
                state = "available (no setup)"
        lines.append(f"[{e['source_tag']}] {tid}: {state}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Lint and query research-stack focus lenses.")
    ap.add_argument("command", choices=["lint", "suggest", "plan", "probe", "table", "docs"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--free", action="store_true", help="probe: treat paid tools as skipped")
    a = ap.parse_args(argv)
    try:
        p = paths(a.root)
        manifest, registry = load(p["manifest"]), load(p["registry"])
    except (OSError, ValueError) as e:
        print(f"cannot load focus files: {e}", file=sys.stderr)
        return 2

    if a.command == "lint":
        errors = lint(a.root)
        for e in errors:
            print(f"FAIL {e}")
        print(f"focus lint: {'FAIL' if errors else 'PASS'} "
              f"({len(manifest['tags'])} tags, {len(manifest['bundles'])} bundles, "
              f"{len(registry)} tools, {len(errors)} problems)")
        return 1 if errors else 0
    if a.command == "suggest":
        if not a.args:
            print("suggest needs a topic", file=sys.stderr)
            return 2
        hits = suggest(" ".join(a.args), manifest)
        for tag, words in hits:
            print(f"{tag}\t(matched: {', '.join(words)})")
        if not hits:
            print("no focus suggested")
        return 0
    if a.command == "plan":
        tags, unknown = expand(a.args, manifest)
        if unknown or not tags:
            print(f"unknown focus: {', '.join(unknown) or '(none given)'}; known: "
                  f"{', '.join(manifest['tags'])}; bundles: {', '.join(manifest['bundles'])}")
            return 1
        print(plan(tags, manifest, registry))
        return 0
    if a.command == "probe":
        tags, unknown = expand(a.args, manifest)
        if unknown:
            print(f"unknown focus: {', '.join(unknown)}")
            return 1
        print(probe(tags, registry, a.free))
        return 0
    if a.command == "table":
        print(table(registry))
        return 0
    ok, msg = docs_in_sync(p, registry)
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
