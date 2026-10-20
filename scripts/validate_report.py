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
FOCUS_LINE_RE = re.compile(r"^(?:focus|'focus'|\"focus\")[ \t]*:(?=[ \t]|$)[ \t]*(.*)$", re.MULTILINE)
DEPTH_LINE_RE = re.compile(r"^(?:depth|'depth'|\"depth\")[ \t]*:(?=[ \t]|$)[ \t]*(.*)$", re.MULTILINE)
# Dashboard lines a --deep run must record (SKILL.md Steps 6.6 and 8.5). A run can skip a
# step silently and still pass structure; these lines make the skip visible.
PERSPECTIVES_RE = re.compile(r"^\W*Perspectives:\s*(.*)$", re.MULTILINE | re.IGNORECASE)
ATTRIBUTION_RE = re.compile(r"^\W*Attribution:\s*.*?(\d+)\s*/\s*(\d+)", re.MULTILINE | re.IGNORECASE)
INTERNAL_RE = re.compile(r"^\W*Internal round:\s*(.*)$", re.MULTILINE | re.IGNORECASE)


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def display_tag(tag):
    """Escape diagnostic controls without changing the parsed tag identity."""
    return ''.join('\\\\' if char == '\\' else char if char.isprintable() else char.encode('unicode_escape').decode('ascii')
                   for char in tag)


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


def reserved_hashtag(tag, manifest):
    """Keep complete custom names and known legacy prefixes out of comments."""
    token = tag.lstrip("#").lower()
    names = set(manifest.get("tags", {})) | set(manifest.get("bundles", {}))
    return any(token == name or (token.startswith(name) and name
                   and not re.match(r"[\w-]", token[len(name):len(name) + 1]))
               for name in names)


def scan_focus_value(value, *, legacy_hashtags=True, comma_positions=None, manifest=None):
    """Scan nodes once; optionally retain unquoted comma offsets for CSV splitting."""
    manifest = manifest or MANIFEST
    if legacy_hashtags:
        leading_tag = re.match(r"^#[^ \t,]+", value)
        if leading_tag:
            tail = value[leading_tag.end():]
            if tail[:1] in (" ", "\t") and tail.strip(" \t") and tail.lstrip(" \t")[0] not in ",#":
                tag = leading_tag.group(0)[1:].lower()
                reserved = reserved_hashtag(tag, manifest)
                return "", None, reserved
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
        if char in " \t":
            index += 1
            continue
        if node_start and char in "&!":
            prop = NODE_PROPERTY_RE.match(value, index)
            if prop:
                index = prop.end()
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
                    and index + 1 < len(value) and value[index + 1] not in " \t"):
                last_nonspace = char
                node_start = False
                index += 1
                continue
            if (index > 0 and value[index - 1] in " \t") or (
                index == 0 and (not legacy_hashtags or len(value) == 1 or value[1] in " \t")
            ):
                prefix = value[:index].rstrip(" \t")
                trailing_tag = re.match(r"#([^ \t,]+)", value[index:])
                tag = trailing_tag.group(1).lower() if trailing_tag else ""
                reserved = reserved_hashtag(tag, manifest)
                ambiguous = bool(legacy_hashtags and (
                    reserved or re.match(r"#[\w-]", value[index:index + 2])))
                return prefix, None, ambiguous
            node_start = False
        else:
            node_start = False
        last_nonspace = char
        index += 1
    return value, quote, False


def focus_value_parts(value, manifest=None):
    """Return the comment-free value and any quote left open on this line."""
    return scan_focus_value(value, manifest=manifest)[:2]


def focus_value_without_comment(value, manifest=None):
    """Keep quoted hashes and existing hashtag tags; drop YAML trailing comments."""
    return focus_value_parts(value, manifest)[0]


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
    if match:
        raw_metadata = match.group(1).replace("\r\n", "\n")
        if any(char in raw_metadata for char in "\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029"):
            return None, "unsupported metadata line separator; use LF or CRLF"
        if RAW_METADATA_CHARACTER_RE.search(raw_metadata):
            return None, "unsupported raw metadata character; use a quoted escape"
    if not match and re.match(r"\A\s*---(?=\s|$)", text):
        return None, "front matter has unsupported opening or closing delimiters"
    return match, None


def metadata_row_ignored(row):
    """Only YAML ASCII separation can make a whole row blank or a comment."""
    content = row.lstrip(" \t")
    return not content or content.startswith("#")


def normalized_front_matter(text):
    """Normalize the shared root indent while preserving nested mapping depth."""
    m, _ = front_matter_envelope(text)
    if not m:
        return ""
    rows = m.group(1).replace("\r\n", "\n").split("\n")
    first = next((row for row in rows if not metadata_row_ignored(row)), "")
    root_indent = len(first) - len(first.lstrip(" "))
    # YAML root mappings may share an indent. Remove only that root prefix, so
    # unrelated nested mappings and block scalar contents stay below root level.
    prefix = " " * root_indent
    return "\n".join(row[root_indent:] if row.startswith(prefix) else row for row in rows)


# This bounded header subset excludes raw controls, including DEL/C1; quoted
# escape spellings retain their YAML meaning without inserting raw header bytes.
RAW_METADATA_CHARACTER_RE = re.compile(r"[^\t\n\x20-\x7e\xa0-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]")
TAG_URI_CHAR = r"(?:%[0-9A-Fa-f]{2}|[0-9A-Za-z#;/?:@&=+$,_.!~*'()\[\]-])"
TAG_SUFFIX_CHAR = r"(?:%[0-9A-Fa-f]{2}|[0-9A-Za-z#;/?:@&=+$_.~*'()-])"
TAG_PROPERTY = r"(?:!<" + TAG_URI_CHAR + r"+>|!(?:!" + TAG_SUFFIX_CHAR + r"+|[0-9A-Za-z-]+!" + TAG_SUFFIX_CHAR + r"+|" + TAG_SUFFIX_CHAR + r"*))"
NODE_PROPERTY_TOKEN = r"(?:&[^\s\[\]{},]+|" + TAG_PROPERTY + r")(?:[ \t]+|(?=[,\]}])|$)"
NODE_PROPERTY_RE = re.compile(NODE_PROPERTY_TOKEN)
NODE_PROPERTIES_RE = re.compile(r"(?:" + NODE_PROPERTY_TOKEN + r")+")


def node_properties_match(value, index=0):
    """Accept at most one anchor and one tag in a node's property prefix."""
    match = NODE_PROPERTIES_RE.match(value, index)
    if match:
        seen = set()
        for token in NODE_PROPERTY_RE.finditer(value, index, match.end()):
            kind = value[token.start()]
            if kind in seen:
                return None
            seen.add(kind)
    return match


YAML_ESCAPES = {"0": "\0", "a": "\a", "b": "\b", "t": "\t", "\t": "\t",
                "n": "\n", "v": "\v", "f": "\f", "r": "\r", "e": "\x1b",
                " ": " ", '"': '"', "/": "/", "\\": "\\", "N": "\x85",
                "_": "\xa0", "L": "\u2028", "P": "\u2029"}


def yaml_escape(value, index):
    """Validate and decode one YAML double-quoted escape without rescanning."""
    escape = value[index + 1:index + 2]
    width = {"x": 2, "u": 4, "U": 8}.get(escape)
    if width is not None:
        digits = value[index + 2:index + 2 + width]
        if len(digits) != width or any(c not in "0123456789abcdefABCDEF" for c in digits):
            return None, index, "invalid hexadecimal escape in quoted metadata"
        codepoint = int(digits, 16)
        if codepoint > 0x10FFFF:
            return None, index, "quoted metadata escape exceeds the Unicode range"
        # Retain the earlier decoder's adjacent JSON-style u-pair identity.
        if escape == "u" and 0xD800 <= codepoint <= 0xDBFF and value[index + 6:index + 8] == "\\u":
            low_digits = value[index + 8:index + 12]
            if len(low_digits) == 4 and all(c in "0123456789abcdefABCDEF" for c in low_digits):
                low = int(low_digits, 16)
                if 0xDC00 <= low <= 0xDFFF:
                    return chr(0x10000 + ((codepoint - 0xD800) << 10) + low - 0xDC00), index + 12, None
        return chr(codepoint), index + 2 + width, None
    if escape in YAML_ESCAPES:
        return YAML_ESCAPES[escape], index + 2, None
    return None, index, "unsupported escape in quoted metadata"


MAPPING_KEY_RE = re.compile(r"^([A-Za-z_][\w.-]*(?: +[\w.-]+)*|'[^'\n]*'|\"(?:[^\"\\\n]|\\.)*\")[ \t]*:(?=[ \t]|$)")


def metadata_value_problem(value, *, focus_csv=False, root_sentinel=False):
    """Prove a node ends on this line; never treat nested flow text as root rows.

    Foreign plain scalars retain literal punctuation. Quotes and flow brackets
    start syntax only at a node boundary, including mapping values in a flow.
    Multiline quoted/flow nodes are explicitly outside the supported grammar.
    Focus alone keeps its established CSV and hashtag shorthand.
    """
    # Each collection owns its current entry and optional key/value separator.
    stack = []
    quote = None
    node_start = True
    completed = False
    index = 0
    while index < len(value):
        char = value[index]
        if stack and char == "\\":
            stack[-1]["backslash"] = True
            if not stack[-1]["pair"]:
                stack[-1]["key_backslash"] = True
        if quote:
            if quote == '"' and char == "\\":
                _, index, problem = yaml_escape(value, index)
                if problem:
                    return problem
                continue
            if char == quote:
                if quote == "'" and value[index + 1:index + 2] == "'":
                    index += 2
                    continue
                quote = None
                completed = True
            index += 1
            continue
        if char in " \t":
            index += 1
            continue
        if char == "#" and (node_start or value[index - 1:index] in (" ", "\t")):
            if not (focus_csv and node_start and value[index + 1:index + 2] and value[index + 1] not in " \t"):
                break
        if char in "]}" and stack:
            frame = stack.pop()
            if char != frame["end"]:
                return "mismatched flow collection delimiters in metadata"
            if frame["end"] == "}" and not frame["pair"] and frame["key_backslash"]:
                return "unsupported escape in metadata mapping key"
            if stack and frame["backslash"]:
                stack[-1]["backslash"] = True
                if not stack[-1]["pair"]:
                    stack[-1]["key_backslash"] = True
            node_start, completed = False, True
        elif char == "," and (stack or focus_csv):
            if stack:
                frame = stack[-1]
                if not frame["entry"]:
                    return "missing entry in a flow metadata collection"
                if frame["end"] == "}" and not frame["pair"] and frame["key_backslash"]:
                    return "unsupported escape in metadata mapping key"
                frame["entry"], frame["pair"], frame["key_backslash"] = False, False, False
            node_start, completed = True, False
        elif char == ":" and stack and (
            completed or not value[index + 1:index + 2] or value[index + 1] in " \t,[]{}"
        ):
            frame = stack[-1]
            if not frame["entry"]:
                return "missing key in a flow metadata mapping"
            if frame["pair"]:
                return "repeated mapping value separator in flow metadata"
            if frame["key_backslash"]:
                return "unsupported escape in metadata mapping key"
            frame["pair"] = True
            node_start, completed = True, False
        elif char == ":" and not stack and (index + 1 == len(value) or value[index + 1] in " \t"):
            return "unsupported mapping key or colon in a plain metadata scalar"
        elif completed:
            return "unsupported text after a quoted or flow metadata value"
        elif node_start:
            properties = node_properties_match(value, index)
            if properties:
                if stack:
                    stack[-1]["entry"] = True
                index = properties.end()
                continue
            if char in "&!":
                return "unsupported or malformed metadata node properties"
            if char == "*":
                return "alias nodes are unsupported in metadata; use the value directly"
            if char in "]},%@`":
                return "reserved indicator cannot start a plain metadata scalar"
            if stack and char in "|>":
                return "block scalar indicators are unsupported in flow metadata"
            if char == "?" and (index + 1 == len(value) or value[index + 1] in " \t"):
                return "unsupported explicit mapping key in metadata"
            if char == "-" and (index + 1 == len(value) or value[index + 1] in " \t"
                                or (stack and value[index + 1] in ",]}")):
                lookahead = index + 1
                while lookahead < len(value) and value[lookahead] in " \t":
                    lookahead += 1
                if not (focus_csv or (root_sentinel and not stack)):
                    return "unsupported sequence indicator inside an inline metadata value"
                if (lookahead < len(value) and value[lookahead] != "#"
                        and not (focus_csv and value[lookahead] in ",]")):
                    return "unsupported sequence indicator inside an inline metadata value"
            node_start = False
            if stack:
                stack[-1]["entry"] = True
            if char in "\"'":
                quote = char
            elif char in "[{":
                stack.append({"end": "]" if char == "[" else "}",
                              "entry": False, "pair": False,
                              "key_backslash": False, "backslash": False})
                node_start = True
            elif not stack and not focus_csv:
                # A colon plus separation is a mapping boundary, not plain text.
                # Unknown key grammar must not conceal a following quoted value.
                plain = re.split(r"[ \t]#", value[index:], maxsplit=1)[0]
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
        meaningful = [row for row in rows if not metadata_row_ignored(row)]
        if meaningful:
            root_indent = len(meaningful[0]) - len(meaningful[0].lstrip(" "))
            if any(len(row) - len(row.lstrip(" ")) < root_indent for row in meaningful):
                return "inconsistent root indentation in metadata"
    active_key = None
    completed_inline_indent = None
    focus_item_indent = None
    block_indent = None
    block_content_indent = None
    indent_levels = [0]
    mapping_values = {}  # Whether the latest key at this level has an empty value.
    sequence_levels = set()
    indentless_sequences = set()
    pending_parent_indent = None
    pending_property_kinds = set()
    for row in normalized_front_matter(text).splitlines():
        spaces = len(row) - len(row.lstrip(" "))
        # A scalar ends at its parent, not at an invalid partial dedent.
        if block_indent is not None:
            if not row.strip(" \t"):
                continue
            if spaces > block_indent:
                if block_content_indent is None:
                    block_content_indent = spaces
                if spaces >= block_content_indent:
                    continue
                if not metadata_row_ignored(row):
                    return "invalid indentation in metadata block scalar"
        block_indent = block_content_indent = None
        if metadata_row_ignored(row):
            continue
        if "\t" in re.match(r"[ \t]*", row).group(0):
            return "tab indentation is unsupported in metadata; use spaces"
        if completed_inline_indent is not None and spaces > completed_inline_indent:
            return "indented rows follow a completed inline metadata value"
        content = row[spaces:]
        starts_sequence = content.startswith("-") and (len(content) == 1 or content[1] in " \t")
        leading_key = None if starts_sequence else MAPPING_KEY_RE.match(content)
        # Only mappings and sequences establish container levels. Properties and
        # standalone values remain attached to their actual pending owner.
        if starts_sequence or leading_key:
            if spaces < indent_levels[-1]:
                while indent_levels[-1] > spaces:
                    expired = indent_levels.pop()
                    mapping_values.pop(expired, None)
                    sequence_levels.discard(expired)
                    indentless_sequences.discard(expired)
                if spaces != indent_levels[-1]:
                    return "metadata dedent does not return to an established indentation level"
            if spaces > indent_levels[-1]:
                indent_levels.append(spaces)
        sequence_width = 0
        last_dash_width = 0
        while (sequence_width < len(content) and content[sequence_width] == "-"
               and (sequence_width + 1 == len(content)
                    or content[sequence_width + 1] in " \t")):
            start = sequence_width
            sequence_indent = spaces + start
            if sequence_indent in mapping_values:
                if not mapping_values[sequence_indent] and sequence_indent not in indentless_sequences:
                    return "sequence items follow an inline metadata value"
                indentless_sequences.add(sequence_indent)
            else:
                sequence_levels.add(sequence_indent)
            if spaces + start > indent_levels[-1]:
                indent_levels.append(spaces + start)
            sequence_width += 1
            while sequence_width < len(content) and content[sequence_width] in " \t":
                sequence_width += 1
            last_dash_width = sequence_width - start
        content = content[sequence_width:]
        if active_key == "focus" and sequence_width:
            if focus_item_indent is not None and spaces != focus_item_indent:
                return "focus sequence items must use consistent indentation"
            focus_item_indent = spaces
        # A sequence item can carry properties on its mapping node. Resolve the
        # mapping boundary after those properties, before inspecting its value.
        properties = node_properties_match(content) if sequence_width else None
        mapping_content = content[properties.end():] if properties else content
        key = MAPPING_KEY_RE.match(mapping_content) if sequence_width else leading_key
        if key and spaces + sequence_width in sequence_levels:
            return "mapping keys and sequence items share a metadata container"
        if key and spaces + sequence_width > indent_levels[-1]:
            indent_levels.append(spaces + sequence_width)
        if key and "\\" in key.group(1):
            return "unsupported escape in metadata mapping key"
        value = mapping_content[key.end():].lstrip(" \t") if key else content
        key_name = key.group(1) if key else None
        if key_name and key_name[0] in "\"'" and key_name[-1] == key_name[0]:
            key_name = key_name[1:-1]  # Inner quotes belong to the literal key.
        problem = metadata_value_problem(
            value, focus_csv=(spaces == 0 and not sequence_width and key_name == "focus")
            or (key is None and active_key == "focus" and bool(sequence_width)),
            root_sentinel=(spaces == 0 and not sequence_width and key_name == "depth"))
        if problem:
            return problem
        properties = node_properties_match(value)
        property_kinds = {value[token.start()] for token in
                          NODE_PROPERTY_RE.finditer(value, 0, properties.end())} if properties else set()
        unadorned = value[properties.end():] if properties else value
        block = re.match(r"^[|>]([+-]?[1-9]?|[1-9][+-]?)?(?:[ \t]+#.*)?$", unadorned.strip(" \t"))
        if unadorned.startswith(("|", ">")) and not block:
            return "invalid metadata block scalar header"
        standalone_owner = pending_parent_indent if key is None and not sequence_width else None
        if key is None and not sequence_width:
            if standalone_owner is None or spaces <= standalone_owner:
                return "standalone metadata values or properties require an empty parent"
        if standalone_owner is not None:
            if pending_property_kinds & property_kinds:
                return "duplicate metadata node property across continuation rows"
            pending_property_kinds.update(property_kinds)
        else:
            # A mapping value or sequence item starts its own node; properties
            # on its owning collection or mapping are not properties on it.
            pending_property_kinds = property_kinds
        if block:
            block_indent = (pending_parent_indent if key is None and not sequence_width else
                            spaces + sequence_width - (last_dash_width if key is None else 0))
            explicit_indent = re.search(r"[1-9]", block.group(1) or "")
            block_content_indent = block_indent + int(explicit_indent.group(0)) if explicit_indent else None
        # Sequence mappings may have sibling keys aligned after the dash. Only
        # deeper rows would make this completed value an unsupported parent.
        has_inline_value = not metadata_row_ignored(unadorned)
        if pending_parent_indent is not None and (key or sequence_width or has_inline_value):
            if pending_parent_indent in mapping_values:
                mapping_values[pending_parent_indent] = False
        if key:
            mapping_indent = spaces + sequence_width
            mapping_values[mapping_indent] = not has_inline_value
            indentless_sequences.discard(mapping_indent)
            pending_parent_indent = None if has_inline_value else mapping_indent
        elif sequence_width:
            pending_parent_indent = None if has_inline_value else spaces + sequence_width - last_dash_width
        elif has_inline_value:
            pending_parent_indent = None
        if pending_parent_indent is None:
            pending_property_kinds.clear()
        # Property-only continuation rows preserve their node's owning parent.
        completed_inline_indent = (
            (standalone_owner if standalone_owner is not None else
             spaces + sequence_width - (last_dash_width if key is None else 0))
            if has_inline_value else None
        )
        if spaces:
            continue
        if active_key is not None and sequence_width:
            continue  # An indentless sequence belongs to the preceding empty root key.
        if sequence_width or not key:
            return "unsupported root mapping/key syntax; use ordinary key: value rows"
        active_key = key_name
        focus_item_indent = None
    return None


def focus_front_matter(text):
    """Return the resolved focus header and root-normalized following rows, or None."""
    front = normalized_front_matter(text)
    line = FOCUS_LINE_RE.search(front)
    if not line:
        return None
    header, rest = line.group(1).strip(" \t"), front[line.end() :].split("\n")[1:]
    first_value = next((row for row in rest if not metadata_row_ignored(row)), "")
    if header.startswith("#") and DASH_ROW_RE.match(first_value):
        header = ""  # A following sequence makes the whole header a YAML comment.
    return header, rest


def checked_focus_value(value, manifest=None):
    """Use one scanner and every diagnostic for headers and accepted block items."""
    scalar, open_quote, ambiguous_hashtags = scan_focus_value(value, manifest=manifest)
    if ambiguous_hashtags:
        return scalar, "hashtags separated by spaces: use a list or commas"
    if open_quote:
        return scalar, "a quoted value does not close on the same line"
    if scalar.startswith("[") and "]" not in scalar:
        return scalar, "the flow list wraps onto the next line"
    return scalar, None


def focus_form_problem(text, manifest=None):
    """Name a `focus:` spelling this parser does not read, or None when it reads every row.

    A hand-rolled reader cannot follow YAML scalars and flow lists that wrap or start on a
    later line. Returning no tags for them would skip every focus check, so check_focus fails
    them instead and asks for a form the parser reads.
    """
    manifest = manifest or MANIFEST
    problem = root_mapping_problem(text)
    if problem:
        return problem
    if len(list(FOCUS_LINE_RE.finditer(normalized_front_matter(text)))) > 1:
        return "duplicate root focus keys are ambiguous"
    parsed = focus_front_matter(text)
    if not parsed:
        return None
    header, rows = parsed
    raw_focus = FOCUS_LINE_RE.search(normalized_front_matter(text)).group(1).strip(" \t")
    first_value = next((row for row in rows if not metadata_row_ignored(row)), "")
    if raw_focus.startswith("#") and DASH_ROW_RE.match(first_value):
        if any(reserved_hashtag(tag, manifest) for tag in re.findall(r"(?:^|[ \t,])#([^ \t,]+)", raw_focus)):
            return "a known hashtag before a block list is ambiguous"
    value, problem = checked_focus_value(header, manifest)
    if problem:
        return problem
    for row in rows:
        if metadata_row_ignored(row):
            continue
        if DASH_ROW_RE.match(row):
            if value:
                return "list items follow an inline value"
            item = DASH_ROW_RE.sub("", row, count=1).lstrip(" \t")
            if re.match(r"^#[^ \t]", item):
                return "an unquoted block hashtag is ambiguous: use - tag or quote it"
            _, problem = checked_focus_value(item, manifest)
            if problem:
                return problem
        elif row[:1] in " \t":
            return "a value starts or continues on a later line"
        else:
            break
    return None


def scalar_value(value):
    """Remove exactly one quoting pair and preserve escaped scalar content."""
    value = value.strip(" \t")
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    if len(value) >= 2 and value[0] == value[-1] == '"':
        decoded = []
        index = 1
        while index < len(value) - 1:
            if value[index] == "\\":
                char, end, problem = yaml_escape(value, index)
                if problem or end > len(value) - 1:
                    return value  # Invalid escapes cannot become a no-focus sentinel.
                decoded.append(char)
                index = end
            else:
                decoded.append(value[index])
                index += 1
        return "".join(decoded)
    return value


def focus_csv_items(value, manifest=None):
    """Split unquoted commas from one shared forward scan."""
    positions = []
    scan_focus_value(value, comma_positions=positions, manifest=manifest)
    start = 0
    for index in positions:
        yield value[start:index]
        start = index + 1
    yield value[start:]


def declared_focus(text, manifest=None):
    """Return focus only after establishing its metadata and sequence boundaries."""
    if root_mapping_problem(text):
        return []
    parsed = focus_front_matter(text)
    if not parsed:
        return []
    header, rest = parsed
    raw = focus_value_without_comment(header, manifest).strip(" \t")
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    if not raw:
        # YAML block list: "focus:" then "  - seo" lines. Without this a report could declare
        # focus in block form and skip every focus check.
        items = []
        for row in rest:
            if metadata_row_ignored(row):
                continue
            item = DASH_ROW_RE.match(row)
            if not item:
                break
            value = row[item.end():].strip(" \t")
            # A leading hash in a block item is a YAML comment, so the item is null.
            items.append("" if value.startswith("#") else focus_value_without_comment(value, manifest))
        raw = ",".join(items)
    tags = [
        scalar_value(t).lstrip("#").lower() for t in focus_csv_items(raw, manifest) if t.strip(" \t")
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
    value = value.strip(" \t")
    for row in front[d.end():].splitlines():
        if metadata_row_ignored(row):
            continue
        if DASH_ROW_RE.match(row):
            return "", "sequence-valued depth is unsupported; use one scalar depth value"
        if row[:1] not in " \t":
            break
        if value:
            return scalar_value(value).lower(), "depth continues on an unsupported later line"
        candidate, open_quote, _ = scan_focus_value(row.strip(" \t"), legacy_hashtags=False)
        if open_quote or not re.fullmatch(r"(?:[\w-]+|'(?:[^']|'')*'|\"(?:[^\"\\]|\\.)*\")", candidate.strip(" \t")):
            return "", "unsupported next-line depth value; use depth: deep or default"
        value = candidate.strip(" \t")
    value = scalar_value(value).lower()
    if value and value not in {"auto-shallow", "default", "deep"} | NO_FOCUS:
        return value, "unsupported depth value; use auto-shallow, default or deep"
    return value, None


def declared_depth(text):
    return depth_scalar(text)[0]


def validated_metadata(text, manifest=None):
    """One validated interpretation for proof checks and lens authority consumers."""
    manifest = manifest or MANIFEST
    problem = focus_form_problem(text, manifest)
    depth, depth_problem = depth_scalar(text)
    problem = problem or depth_problem
    tags = [] if problem else expand_focus(declared_focus(text, manifest), manifest)
    unknown = [tag for tag in tags if tag not in manifest.get("tags", {})]
    return {"problem": problem, "focus": tags, "depth": "" if problem else depth, "unknown": unknown}


def metadata_problem(metadata):
    return metadata["problem"] or (
        "unknown focus tag " + repr(metadata["unknown"][0]) if metadata["unknown"] else None)


def check_process(text, *, _metadata=None):
    """On a --deep report, require the dashboard to record the perspectives that ran, the
    attribution spot-check result and the internal round. Missing records are WARN: the
    report may be right, but nobody can tell whether the steps happened."""
    metadata = _metadata if _metadata is not None else validated_metadata(text)
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
    seen = set()
    for tag in tags:
        for t in manifest.get("bundles", {}).get(tag, [tag]):
            if t not in seen:
                seen.add(t)
                out.append(t)
    return out


def has_section(text, alias):
    """True when a markdown heading or a bold lead-in starts with the alias."""
    pattern = r"^\s*(?:#{1,6}\s*|\*\*)" + re.escape(alias)
    return re.search(pattern, text, re.IGNORECASE | re.MULTILINE) is not None


def check_structure(text, *, _metadata=None):
    metadata = _metadata if _metadata is not None else validated_metadata(text)
    problem = metadata_problem(metadata)
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


def check_focus(text, manifest=None, *, _metadata=None):
    """Focus addenda: one required section per declared tag, plus lens sources."""
    manifest = manifest or MANIFEST
    metadata = _metadata if _metadata is not None else validated_metadata(text, manifest)
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
            known = ", ".join(display_tag(name) for name in sorted(lenses)) or "none (manifest not found)"
            printable_tag = display_tag(tag)
            issues.append(f"FAIL: unknown focus tag '{printable_tag}' (known: {known})")
            fail = True
            continue
        if not has_section(text, lens["addendum"]):
            issues.append(f"FAIL: focus '{display_tag(tag)}' needs a '{lens['addendum']}' section")
            fail = True
        if not used.intersection(lens.get("source_tags", [])):
            issues.append(
                f"WARN: focus '{display_tag(tag)}' cites none of its stack "
                f"({', '.join(lens.get('source_tags', []))}); say which tools were unavailable"
            )
    status = "FAIL" if fail else ("WARN" if issues else "PASS")
    printable_tags = ', '.join(display_tag(tag) for tag in tags)
    return status, [f"Focus: {status} ({printable_tags})"] + [f"  - {i}" for i in issues]


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


def check_sources(text, *, _metadata=None):
    metadata = _metadata if _metadata is not None else validated_metadata(text)
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


def check_citations(text, fetch=_default_fetch, timeout=10, cap=30, *, _metadata=None):
    metadata = _metadata if _metadata is not None else validated_metadata(text)
    problem = metadata_problem(metadata)
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
        _, lines = check_focus(text, _metadata=metadata)
        print("\n".join(lines))
        if a.check == "all":
            print("Verdict: FAIL")
        return 1
    results = []
    if a.check in ("structure", "all"):
        results.append(check_structure(text, _metadata=metadata))
    if a.check in ("structure", "focus", "all") and (a.check == "focus" or metadata["focus"]):
        results.append(check_focus(text, _metadata=metadata))
    if a.check in ("process", "all") or (a.check == "structure" and metadata["depth"] == "deep"):
        results.append(check_process(text, _metadata=metadata))
    if a.check == "citations" or (a.check == "all" and not a.offline):
        results.append(check_citations(text, timeout=a.timeout, cap=a.max, _metadata=metadata))
    if a.check in ("sources", "all"):
        results.append(check_sources(text, _metadata=metadata))
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
