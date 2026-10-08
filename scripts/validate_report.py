#!/usr/bin/env python3
"""Validate a research-stack report. Python 3.9+ standard library only.

Usage:
  validate_report.py structure <report.md>
  validate_report.py focus     <report.md>
  validate_report.py citations <report.md> [--timeout 10] [--max 30]
  validate_report.py sources   <report.md>
  validate_report.py all       <report.md> [--offline]

Each check prints a one-line verdict (PASS, WARN or FAIL) and detail lines.
When the report's front matter declares `focus: [tag, ...]`, `structure` also
runs the focus check: every tag must be known (focus/tags.json), its addendum
section must be present, and the report should cite at least one source from
that tag's stack.
Exit 0 on PASS or WARN, 1 on FAIL, 2 on a usage error. The script only reads
the report; it never writes to it, so it is safe as a checklist verifier.
"""

import argparse
import contextlib
import ipaddress
import json
import os
import re
import socket
import ssl
import sys
import threading
import urllib.error
import urllib.request
from urllib.parse import urlparse

# Source tags the report may use. A bracket group counts when every token in it
# starts with one of these, e.g. [PX], [HN:91], [PX + FC:docs.example.com].
TAGS = {
    "PX",
    "WS",
    "FC",
    "HN",
    "RD",
    "X",
    "ACAD",
    "YT",
    "INT",
    "LEX",
    "CODE",
    "LLM-analysis",
    "BR",
    "EXA",
    "TV",
    "NB",
    "CACHE",
    "perspective",
    "AUDIT",
    "GM",
    "GQ",
    "L30",
    "XS",
    "PAR",
    "KAGI",
}


def _find_manifest():
    """Locate focus/tags.json: the standalone layout (../focus) or the ported one
    (../references/focus). RESEARCH_STACK_FOCUS overrides both."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.environ.get("RESEARCH_STACK_FOCUS", ""),
        os.path.join(here, "..", "focus", "tags.json"),
        os.path.join(here, "..", "references", "focus", "tags.json"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def load_manifest(path=None):
    path = path or _find_manifest()
    if not path:
        return {"tags": {}, "bundles": {}}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


MANIFEST = load_manifest()
for _lens in MANIFEST["tags"].values():
    TAGS.update(_lens.get("source_tags", []))

# (aliases, penalty). The first alias is the name printed when missing.
SECTIONS = [
    (("Decision answer", "Key Findings"), 2),
    (("Contradictions",), 2),
    (("Patterns",), 2),
    (("Coverage gaps", "Gaps"), 1),
]

URL_RE = re.compile(r"https?://(?:\[[^\]\s]+\]|[^\s)\]>\"'`/]+)[^\s)\]>\"'`]*")
BRACKET_RE = re.compile(r"\[([^\[\]\n]{1,120})\]")
TOKEN_SPLIT_RE = re.compile(r"\s*(?:\+|,|;)\s*|\s+")

TIER_SCORES = {
    "academic": 10,
    "official": 9,
    "technical": 8,
    "quality_blog": 7,
    "blog": 6,
    "news": 6,
    "community": 5,
    "wiki": 5,
    "social": 4,
    "unknown": 4,
}

# Hostname rules. Exact domains and their subdomains only; paths never grant trust.
DOMAIN_MAP = [
    ("arxiv.org", "academic"),
    ("ieee.org", "academic"),
    ("acm.org", "academic"),
    ("nature.com", "academic"),
    ("science.org", "academic"),
    ("semanticscholar.org", "academic"),
    ("doi.org", "academic"),
    ("scholar.google.com", "academic"),
    ("rfc-editor.org", "technical"),
    ("ietf.org", "technical"),
    ("w3.org", "technical"),
    ("github.com", "technical"),
    ("huggingface.co", "technical"),
    ("modelcontextprotocol.io", "technical"),
    ("docs.python.org", "official"),
    ("learn.microsoft.com", "official"),
    ("cloud.google.com", "official"),
    ("aws.amazon.com", "official"),
    # Vendor engineering blogs are primary sources for their own product
    # status and pricing: the only place a release date or a fee is announced.
    ("blog.cloudflare.com", "quality_blog"),
    ("blog.google", "quality_blog"),
    ("simonwillison.net", "quality_blog"),
    ("medium.com", "blog"),
    ("dev.to", "blog"),
    ("substack.com", "blog"),
    ("techcrunch.com", "news"),
    ("theverge.com", "news"),
    ("arstechnica.com", "news"),
    ("stackoverflow.com", "community"),
    ("stackexchange.com", "community"),
    ("reddit.com", "community"),
    ("news.ycombinator.com", "community"),
    ("hn.algolia.com", "community"),
    ("wikipedia.org", "wiki"),
    ("twitter.com", "social"),
    ("x.com", "social"),
    ("linkedin.com", "social"),
]


def lens_authorities(tags, manifest=None):
    """Authorities of the active lenses only. A report on one area should not gain trust for
    citing another lens's domains (youtube.com is an authority for content, not for security)."""
    manifest = manifest or MANIFEST
    known = {d for d, _ in DOMAIN_MAP}
    out = []
    for tag in tags:
        for domain in manifest.get("tags", {}).get(tag, {}).get("authorities", []):
            if domain not in known and domain not in out:
                out.append(domain)
    return out

NO_FOCUS = {"none", "null", "~", "-"}
FRONT_MATTER_RE = re.compile(r"\A\s*---[ \t]*\r?\n(.*?)^---[ \t]*(?:\r?\n|\Z)", re.DOTALL | re.MULTILINE)
FOCUS_LINE_RE = re.compile(r"^(?:focus|'focus'|\"focus\")[ \t]*:[ \t]*(.*)$", re.MULTILINE)
DEPTH_LINE_RE = re.compile(r"^(?:depth|'depth'|\"depth\")[ \t]*:[ \t]*(.*)$", re.MULTILINE)
# Dashboard lines a --deep run must record (SKILL.md Steps 6.6 and 8.5). A run can skip a
# step silently and still pass structure; these lines make the skip visible.
PERSPECTIVES_RE = re.compile(r"^\W*Perspectives:\s*(.*)$", re.MULTILINE | re.IGNORECASE)
ATTRIBUTION_RE = re.compile(r"^\W*Attribution:\s*.*?(\d+)\s*/\s*(\d+)", re.MULTILINE | re.IGNORECASE)
INTERNAL_RE = re.compile(r"^\W*Internal round:\s*(.*)$", re.MULTILINE | re.IGNORECASE)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def extract_urls(text):
    urls = [u.rstrip(".,;:!?") for u in URL_RE.findall(text)]
    return list(dict.fromkeys(urls))


def extract_tags(text):
    """Return every valid tag token found in bracket groups."""
    found = []
    for group in BRACKET_RE.findall(text):
        tokens = [t for t in TOKEN_SPLIT_RE.split(group.strip()) if t]
        heads = [t.split(":", 1)[0] for t in tokens]
        if heads and all(h in TAGS for h in heads):
            found.extend(heads)
    return found


def scan_focus_value(value, *, legacy_hashtags=True, comma_positions=None):
    """Scan nodes once; optionally retain unquoted comma offsets for CSV splitting."""
    if legacy_hashtags:
        leading_tag = re.match(r"^#[\w-]+", value)
        if leading_tag:
            tail = value[leading_tag.end():]
            if tail[:1].isspace() and tail.strip() and tail.lstrip()[0] not in ",#":
                return "", None, False
    quote = None
    flow_depth = 0
    node_start = True
    last_nonspace = None
    index = 0
    while index < len(value):
        char = value[index]
        if quote:
            if quote == '"' and char == "\\":
                index += 2
                continue
            if char == quote:
                if quote == "'" and value[index + 1:index + 2] == "'":
                    index += 2
                    continue
                quote = None
            index += 1
            continue
        if char.isspace():
            index += 1
            continue
        if node_start and char in "&!":
            prop = re.match(r"(?:&[^\s\[\]{},]+|!<[^>]*>|![^\s\[\]{},]*)[ \t]+", value[index:])
            if prop:
                index += prop.end()
                continue
        if char in "\"'" and node_start:
            quote = char
            node_start = False
        elif char in "[{":
            flow_depth += 1
            node_start = True
        elif char in "]}":
            flow_depth = max(0, flow_depth - 1)
            node_start = False
        elif char == ",":
            node_start = True
            if comma_positions is not None:
                comma_positions.append(index)
        elif char == ":" and flow_depth:
            node_start = True
        elif char == "#":
            if (legacy_hashtags and last_nonspace in (",", "[")
                    and index + 1 < len(value) and not value[index + 1].isspace()):
                last_nonspace = char
                node_start = False
                index += 1
                continue
            if (index > 0 and value[index - 1].isspace()) or (
                index == 0 and (not legacy_hashtags or len(value) == 1 or value[1].isspace())
            ):
                prefix = value[:index].rstrip()
                ambiguous = bool(legacy_hashtags and re.search(r"#[\w-]+$", prefix)
                    and index + 1 < len(value) and not value[index + 1].isspace())
                return prefix, None, ambiguous
            node_start = False
        else:
            node_start = False
        last_nonspace = char
        index += 1
    return value, quote, False


def focus_value_parts(value):
    """Return the comment-free value and any quote left open on this line."""
    return scan_focus_value(value)[:2]


def focus_value_without_comment(value):
    """Keep quoted hashes and existing hashtag tags; drop YAML trailing comments."""
    return focus_value_parts(value)[0]


DASH_ROW_RE = re.compile(r"^[ \t]*-(?:[ \t]|$)")


def front_matter_envelope(text):
    """Share encoding/delimiter handling between raw extraction and validation."""
    prefix = re.match(r"[\s\ufeff]*", text).group(0)
    bom_count = prefix.count("\ufeff")
    if bom_count:
        if bom_count != 1 or not text.startswith("\ufeff"):
            return None, "unsupported BOM placement; use one UTF-8 BOM at the document start"
        text = text[1:]
    match = FRONT_MATTER_RE.match(text)
    if not match and re.match(r"\A\s*---(?=\s|$)", text):
        return None, "front matter has unsupported opening or closing delimiters"
    return match, None


def normalized_front_matter(text):
    """Normalize the shared root indent while preserving nested mapping depth."""
    m, _ = front_matter_envelope(text)
    if not m:
        return ""
    rows = m.group(1).replace("\r\n", "\n").split("\n")
    first = next((row for row in rows if row.strip() and not row.lstrip().startswith("#")), "")
    root_indent = len(first) - len(first.lstrip(" "))
    # YAML root mappings may share an indent. Remove only that root prefix, so
    # unrelated nested mappings and block scalar contents stay below root level.
    prefix = " " * root_indent
    return "\n".join(row[root_indent:] if row.startswith(prefix) else row for row in rows)


NODE_PROPERTIES_RE = re.compile(
    r"(?:(?:&[^\s\[\]{},]+|!<[^>]*>|![^\s\[\]{},]*)[ \t]+)+")
MAPPING_KEY_RE = re.compile(r"^([A-Za-z_][\w .-]*|'[^'\n]*'|\"[^\"\n]*\")[ \t]*:")


def metadata_value_problem(value, *, focus_csv=False):
    """Prove a node ends on this line; never treat nested flow text as root rows.

    Foreign plain scalars retain literal punctuation. Quotes and flow brackets
    start syntax only at a node boundary, including mapping values in a flow.
    Multiline quoted/flow nodes are explicitly outside the supported grammar.
    Focus alone keeps its established CSV and hashtag shorthand.
    """
    stack = []
    quote = None
    node_start = True
    completed = False
    index = 0
    while index < len(value):
        char = value[index]
        if quote:
            if quote == '"' and char == "\\":
                index += 2
                continue
            if char == quote:
                if quote == "'" and value[index + 1:index + 2] == "'":
                    index += 2
                    continue
                quote = None
                completed = True
            index += 1
            continue
        if char.isspace():
            index += 1
            continue
        if char == "#" and (node_start or completed or value[index - 1:index].isspace()):
            if not (focus_csv and node_start and value[index + 1:index + 2] and not value[index + 1].isspace()):
                break
        if char in "]}" and stack:
            if char != stack.pop():
                return "mismatched flow collection delimiters in metadata"
            node_start, completed = False, True
        elif char == "," and (stack or focus_csv):
            node_start, completed = True, False
        elif char == ":" and stack and (
            completed or not value[index + 1:index + 2] or value[index + 1].isspace()
        ):
            node_start, completed = True, False
        elif completed:
            return "unsupported text after a quoted or flow metadata value"
        elif node_start:
            properties = NODE_PROPERTIES_RE.match(value, index)
            if properties:
                index = properties.end()
                continue
            node_start = False
            if char in "\"'":
                quote = char
            elif char in "[{":
                stack.append("]" if char == "[" else "}")
                node_start = True
            elif not stack and not focus_csv:
                # A colon plus separation is a mapping boundary, not plain text.
                # Unknown key grammar must not conceal a following quoted value.
                plain = re.split(r"[ \t]+#", value[index:], maxsplit=1)[0]
                if re.search(r":(?:[ \t]|$)", plain):
                    return "unsupported mapping key or colon in a plain metadata scalar"
                return None  # Other punctuation in an ordinary plain scalar is data.
        elif stack and char in "[{":
            return "unsupported flow delimiter inside a plain metadata scalar"
        index += 1
    if quote:
        return "a quoted metadata value does not close on the same line"
    if stack:
        return "a flow metadata collection does not close on the same line"
    return None


def root_mapping_problem(text):
    """Validate structural boundaries before reading apparent root metadata."""
    envelope, problem = front_matter_envelope(text)
    if problem:
        return problem
    if envelope:
        rows = envelope.group(1).splitlines()
        meaningful = [row for row in rows if row.strip() and not row.lstrip().startswith("#")]
        if meaningful:
            root_indent = len(meaningful[0]) - len(meaningful[0].lstrip(" "))
            if any(len(row) - len(row.lstrip(" ")) < root_indent for row in meaningful):
                return "inconsistent root indentation in metadata"
    active_key = None
    block_indent = None
    for row in normalized_front_matter(text).splitlines():
        if not row.strip() or row.lstrip().startswith("#"):
            continue
        spaces = len(row) - len(row.lstrip(" "))
        # Block-scalar contents cannot introduce nodes or root declarations.
        if block_indent is not None and spaces > block_indent:
            continue
        block_indent = None
        if "\t" in re.match(r"[ \t]*", row).group(0):
            return "tab indentation is unsupported in metadata; use spaces"
        content = row[spaces:]
        sequence_width = 0
        last_dash_width = 0
        while DASH_ROW_RE.match(content):
            dash = DASH_ROW_RE.match(content)
            remainder = content[dash.end():]
            last_dash_width = dash.end() + len(remainder) - len(remainder.lstrip(" \t"))
            sequence_width += last_dash_width
            content = content[last_dash_width:]
        # A sequence item can carry properties on its mapping node. Resolve the
        # mapping boundary after those properties, before inspecting its value.
        properties = NODE_PROPERTIES_RE.match(content) if sequence_width else None
        mapping_content = content[properties.end():] if properties else content
        key = MAPPING_KEY_RE.match(mapping_content)
        value = mapping_content[key.end():].lstrip() if key else content
        key_name = key.group(1).strip().strip("\"'") if key else None
        problem = metadata_value_problem(
            value, focus_csv=key_name == "focus" or (key is None and active_key == "focus"))
        if problem:
            return problem
        properties = NODE_PROPERTIES_RE.match(value)
        unadorned = value[properties.end():] if properties else value
        if re.match(r"^[|>](?:[+-]?[1-9]?|[1-9][+-]?)?(?:[ \t]+#.*)?$", unadorned.strip()):
            block_indent = spaces + sequence_width - (last_dash_width if key is None else 0)
        if spaces:
            continue
        if active_key is not None and sequence_width:
            continue  # An indentless sequence belongs to the preceding root key.
        if sequence_width or not key or "\\" in key.group(1):
            return "unsupported root mapping/key syntax; use ordinary key: value rows"
        active_key = key_name
    return None


def focus_front_matter(text):
    """Return the resolved focus header and root-normalized following rows, or None."""
    front = normalized_front_matter(text)
    line = FOCUS_LINE_RE.search(front)
    if not line:
        return None
    header, rest = line.group(1).strip(), front[line.end() :].split("\n")[1:]
    first_value = next((row for row in rest if row.strip() and not row.lstrip().startswith("#")), "")
    if header.startswith("#") and DASH_ROW_RE.match(first_value):
        header = ""  # A following sequence makes the whole header a YAML comment.
    return header, rest


def checked_focus_value(value):
    """Use one scanner and every diagnostic for headers and accepted block items."""
    scalar, open_quote, ambiguous_hashtags = scan_focus_value(value)
    if ambiguous_hashtags:
        return scalar, "hashtags separated by spaces: use a list or commas"
    if open_quote:
        return scalar, "a quoted value does not close on the same line"
    if scalar.startswith("[") and "]" not in scalar:
        return scalar, "the flow list wraps onto the next line"
    return scalar, None


def focus_form_problem(text):
    """Name a `focus:` spelling this parser does not read, or None when it reads every row.

    A hand-rolled reader cannot follow YAML scalars and flow lists that wrap or start on a
    later line. Returning no tags for them would skip every focus check, so check_focus fails
    them instead and asks for a form the parser reads.
    """
    problem = root_mapping_problem(text)
    if problem:
        return problem
    if len(list(FOCUS_LINE_RE.finditer(normalized_front_matter(text)))) > 1:
        return "duplicate root focus keys are ambiguous"
    parsed = focus_front_matter(text)
    if not parsed:
        return None
    header, rows = parsed
    value, problem = checked_focus_value(header)
    if problem:
        return problem
    for row in rows:
        if not row.strip() or row.lstrip().startswith("#"):
            continue
        if DASH_ROW_RE.match(row):
            if value:
                return "list items follow an inline value"
            item = DASH_ROW_RE.sub("", row, count=1).lstrip()
            if re.match(r"^#[^ \t]", item):
                return "an unquoted block hashtag is ambiguous: use - tag or quote it"
            _, problem = checked_focus_value(item)
            if problem:
                return problem
        elif row[:1] in " \t":
            return "a value starts or continues on a later line"
        else:
            break
    return None


def scalar_value(value):
    """Remove exactly one quoting pair and preserve escaped scalar content."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, str) else value
        except ValueError:
            return value  # Unsupported quoted escapes cannot become a no-focus sentinel.
    return value


def focus_csv_items(value):
    """Split unquoted commas from one shared forward scan."""
    positions = []
    scan_focus_value(value, comma_positions=positions)
    start = 0
    for index in positions:
        yield value[start:index]
        start = index + 1
    yield value[start:]


def declared_focus(text):
    """Return focus only after establishing the metadata's root/scalar boundaries."""
    if root_mapping_problem(text):
        return []
    parsed = focus_front_matter(text)
    if not parsed:
        return []
    header, rest = parsed
    raw = focus_value_without_comment(header).strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    if not raw:
        # YAML block list: "focus:" then "  - seo" lines. Without this a report could declare
        # focus in block form and skip every focus check.
        items = []
        for row in rest:
            if not row.strip() or row.lstrip().startswith("#"):
                continue
            item = re.match(r"^[ \t]*-(?:[ \t]+(.*?))?[ \t]*$", row)
            if not item:
                break
            value = item.group(1) or ""
            # A leading hash in a block item is a YAML comment, so the item is null.
            items.append("" if value.startswith("#") else focus_value_without_comment(value))
        raw = ",".join(items)
    tags = [
        scalar_value(t).lstrip("#").lower() for t in focus_csv_items(raw) if t.strip()
    ]
    return [t for t in tags if t not in NO_FOCUS]


def depth_scalar(text):
    """Read the supported scalar depth forms and retain unsupported-form diagnostics."""
    problem = root_mapping_problem(text)
    if problem:
        return "", problem
    front = normalized_front_matter(text)
    matches = list(DEPTH_LINE_RE.finditer(front))
    if len(matches) > 1:
        return "", "duplicate root depth keys are ambiguous"
    if not matches:
        return "", None
    d = matches[0]
    value, open_quote, _ = scan_focus_value(d.group(1), legacy_hashtags=False)
    if open_quote:
        return "", "a quoted depth value does not close on the same line"
    value = value.strip()
    for row in front[d.end():].splitlines():
        if not row.strip() or row.lstrip().startswith("#"):
            continue
        if DASH_ROW_RE.match(row):
            return "", "sequence-valued depth is unsupported; use one scalar depth value"
        if row[:1] not in " \t":
            break
        if value:
            return scalar_value(value).lower(), "depth continues on an unsupported later line"
        candidate, open_quote, _ = scan_focus_value(row.strip(), legacy_hashtags=False)
        if open_quote or not re.fullmatch(r"(?:[\w-]+|'(?:[^']|'')*'|\"(?:[^\"\\]|\\.)*\")", candidate.strip()):
            return "", "unsupported next-line depth value; use depth: deep or default"
        value = candidate.strip()
    value = scalar_value(value).lower()
    if value and value not in {"auto-shallow", "default", "deep"} | NO_FOCUS:
        return value, "unsupported depth value; use auto-shallow, default or deep"
    return value, None


def declared_depth(text):
    return depth_scalar(text)[0]


def validated_metadata(text, manifest=None):
    """One validated interpretation for proof checks and lens authority consumers."""
    manifest = manifest or MANIFEST
    problem = focus_form_problem(text)
    depth, depth_problem = depth_scalar(text)
    problem = problem or depth_problem
    tags = [] if problem else expand_focus(declared_focus(text), manifest)
    unknown = [tag for tag in tags if tag not in manifest.get("tags", {})]
    return {"problem": problem, "focus": tags, "depth": "" if problem else depth, "unknown": unknown}


def metadata_problem(metadata):
    return metadata["problem"] or (
        "unknown focus tag " + repr(metadata["unknown"][0]) if metadata["unknown"] else None)


def check_process(text):
    """On a --deep report, require the dashboard to record the perspectives that ran, the
    attribution spot-check result and the internal round. Missing records are WARN: the
    report may be right, but nobody can tell whether the steps happened."""
    metadata = validated_metadata(text)
    problem = metadata_problem(metadata)
    if problem:
        return "FAIL", [f"Process: FAIL ({problem})"]
    if metadata["depth"] != "deep":
        return "PASS", ["Process: PASS (not a --deep report)"]
    issues = []
    persp = PERSPECTIVES_RE.search(text)
    if not persp or not re.search(r"\d", persp.group(1)):
        issues.append("WARN: no 'Perspectives:' dashboard line with counts (Step 6.6)")
    attr = ATTRIBUTION_RE.search(text)
    if not attr:
        issues.append("WARN: no 'Attribution: N/N' dashboard line (Step 8.5 spot-check)")
    elif int(attr.group(1)) < int(attr.group(2)):
        issues.append(f"WARN: attribution {attr.group(1)}/{attr.group(2)}: fix or drop unsupported claims")
    if not INTERNAL_RE.search(text):
        issues.append("WARN: no 'Internal round:' dashboard line (Round 1.5, or say why it was skipped)")
    status = "WARN" if issues else "PASS"
    return status, [f"Process: {status}"] + [f"  - {i}" for i in issues]


def expand_focus(tags, manifest=None):
    """Expand bundles and drop duplicates, keeping order. Unknown names pass through."""
    manifest = manifest or MANIFEST
    out = []
    for tag in tags:
        for t in manifest.get("bundles", {}).get(tag, [tag]):
            if t not in out:
                out.append(t)
    return out


def has_section(text, alias):
    """True when a markdown heading or a bold lead-in starts with the alias."""
    pattern = r"^\s*(?:#{1,6}\s*|\*\*)" + re.escape(alias)
    return re.search(pattern, text, re.IGNORECASE | re.MULTILINE) is not None


def check_structure(text):
    problem = metadata_problem(validated_metadata(text))
    if problem:
        return "FAIL", [f"Structure: FAIL ({problem})"]
    issues, score = [], 10
    present = 0
    for aliases, penalty in SECTIONS:
        if any(has_section(text, a) for a in aliases):
            present += 1
        else:
            issues.append(f"MISSING: '{aliases[0]}' section")
            score -= penalty
    tags = extract_tags(text)
    types = sorted(set(tags))
    if not tags:
        issues.append("MISSING: no source tags (expected [WS], [FC:domain], ...)")
        score -= 3
    elif len(types) < 2:
        issues.append(f"WARN: only {len(types)} source type, low corroboration")
        score -= 1
    words = len(text.split())
    if words < 200:
        issues.append(f"WARN: only {words} words, possibly incomplete")
        score -= 2
    score = max(0, score)
    status = "FAIL" if present != len(SECTIONS) or not tags else ("PASS" if score >= 7 else ("WARN" if score >= 4 else "FAIL"))
    lines = [
        f"Structure: {status} ({score}/10)",
        f"  Sections: {present}/{len(SECTIONS)}",
        f"  Source tags: {len(tags)} found, {len(types)} types ({', '.join(types) or 'none'})",
        f"  Word count: {words}",
    ] + [f"  - {i}" for i in issues]
    return status, lines


def check_focus(text, manifest=None):
    """Focus addenda: one required section per declared tag, plus lens sources."""
    manifest = manifest or MANIFEST
    metadata = validated_metadata(text, manifest)
    problem = metadata["problem"]
    if problem:
        return "FAIL", [
            f"Focus: FAIL ({problem})",
            "  - write `focus: [a, b]` on one line, or a block list of `- tag` rows",
        ]
    tags = metadata["focus"]
    if not tags:
        return "PASS", ["Focus: PASS (no focus declared)"]
    lenses = manifest.get("tags", {})
    issues, fail = [], False
    used = set(extract_tags(text))
    for tag in tags:
        lens = lenses.get(tag)
        if lens is None:
            known = ", ".join(sorted(lenses)) or "none (manifest not found)"
            issues.append(f"FAIL: unknown focus tag '{tag}' (known: {known})")
            fail = True
            continue
        if not has_section(text, lens["addendum"]):
            issues.append(f"FAIL: focus '{tag}' needs a '{lens['addendum']}' section")
            fail = True
        if not used.intersection(lens.get("source_tags", [])):
            issues.append(
                f"WARN: focus '{tag}' cites none of its stack "
                f"({', '.join(lens.get('source_tags', []))}); say which tools were unavailable"
            )
    status = "FAIL" if fail else ("WARN" if issues else "PASS")
    return status, [f"Focus: {status} ({', '.join(tags)})"] + [f"  - {i}" for i in issues]


def classify_url(url, authorities=()):
    """Tier for a URL. `authorities` are the active lenses' domains, ranked official."""
    try:
        parsed = urlparse(url)
        domain = (parsed.hostname or "").lower().rstrip(".")
    except ValueError:
        return "unknown"
    for pattern, tier in DOMAIN_MAP + [(d, "official") for d in authorities]:
        if domain == pattern or domain.endswith("." + pattern):
            return tier
    if domain.endswith(".edu"):
        return "academic"
    if domain.endswith(".gov"):
        return "official"
    return "unknown"


def check_sources(text):
    metadata = validated_metadata(text)
    problem = metadata_problem(metadata)
    if problem:
        return "FAIL", [f"Source Quality: FAIL ({problem})"]
    urls = extract_urls(text)
    if not urls:
        return "WARN", ["Source Quality: WARN (no URLs found)"]
    authorities = lens_authorities(metadata["focus"])
    tiers = {}
    for url in urls:
        tiers.setdefault(classify_url(url, authorities), []).append(url)
    scores = [TIER_SCORES[t] for t, us in tiers.items() for _ in us]
    avg = sum(scores) / len(scores)
    status = "PASS" if avg >= 6 else ("WARN" if avg >= 4 else "FAIL")
    lines = [f"Source Quality: {status} (avg {avg:.1f}/10)"]
    if avg < 5:
        lines.append("  - WARN: sources are mostly informal")
    for tier in sorted(tiers, key=lambda t: TIER_SCORES[t], reverse=True):
        n = len(tiers[tier])
        lines.append(
            f"  {tier} ({TIER_SCORES[tier]}/10): {n} source{'s' if n != 1 else ''}"
        )
    return status, lines


# ---------------------------------------------------------------------------
# DNS pinning: closes the TOCTOU a rebinding attack relies on. Without this,
# _reject_unsafe_url resolves a host once to check it is public, then urllib
# performs its own, separate resolution when it actually connects -- a host
# that answers public on the first lookup and private (loopback, metadata
# endpoint, etc.) on the second passes the check and is still fetched. The
# fix: for the duration of one fetch (including every redirect hop it
# follows), pin socket.getaddrinfo() to return exactly the address that was
# just validated for a given host, so no second, independent lookup can ever
# happen.
#
# The pin is keyed on a normalised host (lowercased + IDNA-encoded): a host
# written to the cache in one spelling ("Example.com") and read back in
# another ("EXAMPLE.COM", or a Unicode label whose IDNA form is the same
# ASCII name) must hit the same cache entry, not miss it. A miss must never
# fall back to the real, unchecked resolver either -- _pinned_getaddrinfo
# validates-and-pins any host it does not already recognise itself, so at
# most one real lookup ever happens per host for the fetch, and it is always
# the checked one.
# ---------------------------------------------------------------------------
_PINNED_ADDRS = {}
_PIN_LOCK = threading.Lock()
_real_getaddrinfo = socket.getaddrinfo


def _normalize_host(host):
    """Lowercase + IDNA-normalise a hostname so the same host cannot be
    pinned under one spelling and looked up under another."""
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except (UnicodeError, AttributeError):
        ascii_host = host
    return ascii_host.lower()


def _validate_and_pin(host):
    """Resolve host, reject it if it is not a safe public address, and pin
    the result under its normalised form. Returns the safe IP string.

    Shared by _reject_unsafe_url (the URL-level check) and, defensively, by
    _pinned_getaddrinfo for any host it is asked to resolve that is not
    already pinned -- so every real lookup, however it is reached, goes
    through this one gate.
    """
    try:
        infos = _real_getaddrinfo(host, None)
    except OSError as exc:
        raise ValueError(f"could not resolve host {host}: {exc}") from exc
    safe_ip = None
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            not ip.is_global
            or ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_unspecified
            or ip.is_multicast
        ):
            raise ValueError(
                f"refusing host {host}: resolves to {ip} (not a public address)"
            )
        if safe_ip is None:
            safe_ip = str(ip)
    if safe_ip is None:
        raise ValueError(f"no addresses for {host}")
    _PINNED_ADDRS[_normalize_host(host)] = safe_ip
    return safe_ip


def _pinned_getaddrinfo(host, port, *args, **kwargs):
    key = _normalize_host(host)
    ip = _PINNED_ADDRS.get(key)
    if ip is None:
        ip = _validate_and_pin(host)
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port or 0))]


@contextlib.contextmanager
def _dns_pinning():
    """Install the pinned resolver for one fetch. Nestable/reentrant-safe: an
    already-installed pin (e.g. a redirect handled inside another fetch on
    the same thread) is left alone by the inner call."""
    with _PIN_LOCK:
        already = socket.getaddrinfo is _pinned_getaddrinfo
        if not already:
            socket.getaddrinfo = _pinned_getaddrinfo
    try:
        yield
    finally:
        if not already:
            with _PIN_LOCK:
                socket.getaddrinfo = _real_getaddrinfo
                _PINNED_ADDRS.clear()


def _reject_unsafe_url(url):
    """Refuse a URL the validator must never fetch: SSRF guard.

    Blocks anything that is not plain http(s), and any host that resolves to a
    loopback, private, link-local, reserved, unspecified or multicast address
    (cloud metadata endpoints like 169.254.169.254 included). Raises
    ValueError; callers turn that into a "dead"/"BLOCKED" citation rather than
    letting it escape as a crash.

    As a side effect, records the validated address for this host in
    _PINNED_ADDRS (keyed on its normalised form): see _dns_pinning and
    _validate_and_pin above for why.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"refusing non-http(s) scheme: {url}")
    host = parsed.hostname
    if not host:
        raise ValueError(f"no host in URL: {url}")
    try:
        _validate_and_pin(host)
    except ValueError as exc:
        raise ValueError(f"refusing to fetch {url}: {exc}") from exc


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-check every redirect hop: a public URL must not be able to bounce a
    fetch to an internal one."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _reject_unsafe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_SAFE_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _SafeRedirectHandler)


def _default_fetch(url, method, timeout):
    with _dns_pinning():
        _reject_unsafe_url(url)
        req = urllib.request.Request(
            url, method=method, headers={"User-Agent": "research-stack-validator/1.0"}
        )
        with _SAFE_OPENER.open(req, timeout=timeout) as resp:
            return resp.status


def classify_citation(url, fetch=_default_fetch, timeout=10):
    """Return ('live' | 'dead' | 'unverified', detail).

    Cannot-verify is not dead: an auth wall, a bot challenge, a throttle or a
    server error says the page may exist, so it is reported, not failed.
    """
    for method in ("HEAD", "GET"):
        try:
            code = fetch(url, method, timeout)
        except ValueError as e:  # the SSRF guard refused this URL or a redirect hop
            return "dead", f"BLOCKED {url} ({e})"
        except urllib.error.HTTPError as e:
            code = e.code
            try:  # an HTTPError built without a body cannot be closed on Python 3.9
                e.close()
            except (AttributeError, KeyError, OSError):
                pass
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, ssl.SSLError):
                return "unverified", f"TLS {url}"
            if isinstance(reason, (TimeoutError, socket.timeout)):
                return "unverified", f"TIMEOUT {url}"
            return "dead", f"ERR {url} ({type(reason).__name__})"
        except (TimeoutError, OSError) as e:
            return "unverified", f"TIMEOUT {url} ({type(e).__name__})"
        if code < 400:
            return "live", ""
        if code in (405, 501) and method == "HEAD":
            continue  # HEAD refused, try GET
        if code in (401, 403, 405, 429) or code >= 500:
            return "unverified", f"UNVERIFIED({code}) {url}"
        return "dead", f"{code} {url}"
    return "unverified", f"UNVERIFIED {url}"


def check_citations(text, fetch=_default_fetch, timeout=10, cap=30):
    problem = metadata_problem(validated_metadata(text))
    if problem:
        return "FAIL", [f"Citations: FAIL ({problem})"]
    urls = extract_urls(text)
    if not urls:
        return "WARN", ["Citations: WARN (no URLs found)"]
    counts = {"live": 0, "dead": 0, "unverified": 0}
    details = []
    for url in urls[:cap]:
        kind, detail = classify_citation(url, fetch, timeout)
        counts[kind] += 1
        if detail:
            details.append(f"  {detail}")
    dead = counts["dead"]
    status = "PASS" if dead <= 2 else ("WARN" if dead <= 5 else "FAIL")
    lines = [
        f"Citations: {status} ({counts['live']} live / {dead} dead / "
        f"{counts['unverified']} unverified / {min(len(urls), cap)} checked)"
    ]
    if len(urls) > cap:
        lines.append(f"  - {len(urls) - cap} URLs not checked (cap {cap})")
    return status, lines + details[:10]


def main(argv=None):
    p = argparse.ArgumentParser(description="Validate a research-stack report.")
    p.add_argument("check", choices=["structure", "focus", "process", "citations", "sources", "all"])
    p.add_argument("report")
    p.add_argument("--timeout", type=float, default=10)
    p.add_argument("--max", type=int, default=30, help="max URLs to check")
    p.add_argument("--offline", action="store_true", help="skip the citation check")
    a = p.parse_args(argv)
    try:
        text = read(a.report)
    except OSError as e:
        print(f"cannot read report: {e}", file=sys.stderr)
        return 2
    metadata = validated_metadata(text)
    if metadata_problem(metadata):
        # Reject unsupported declarations before any caller can skip checks, grant
        # lens authority, or make a citation request from malformed metadata.
        _, lines = check_focus(text)
        print("\n".join(lines))
        if a.check == "all":
            print("Verdict: FAIL")
        return 1
    results = []
    if a.check in ("structure", "all"):
        results.append(check_structure(text))
    if a.check in ("structure", "focus", "all") and (a.check == "focus" or metadata["focus"]):
        results.append(check_focus(text))
    if a.check in ("process", "all") or (a.check == "structure" and metadata["depth"] == "deep"):
        results.append(check_process(text))
    if a.check == "citations" or (a.check == "all" and not a.offline):
        results.append(check_citations(text, timeout=a.timeout, cap=a.max))
    if a.check in ("sources", "all"):
        results.append(check_sources(text))
    for _, lines in results:
        print("\n".join(lines))
    statuses = [s for s, _ in results]
    if a.check == "all":
        verdict = (
            "FAIL" if "FAIL" in statuses else ("WARN" if "WARN" in statuses else "PASS")
        )
        print(f"Verdict: {verdict}")
    return 1 if "FAIL" in statuses else 0


if __name__ == "__main__":
    sys.exit(main())
