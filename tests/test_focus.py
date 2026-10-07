"""Tests for focus lenses: validator focus checks and focus_check.py. Run: python3 -m unittest discover tests"""

import io
import re
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import focus_check as fc  # noqa: E402
import validate_report as vr  # noqa: E402

FIX = ROOT / "tests/fixtures"
MANIFEST = json.loads((ROOT / "focus/tags.json").read_text())


def run(fn, argv):
    out = io.StringIO()
    with redirect_stdout(out):
        code = fn(argv)
    return code, out.getvalue()


class ValidatorFocusTest(unittest.TestCase):
    def test_lens_source_tags_are_known_to_the_validator(self):
        for tag, lens in MANIFEST["tags"].items():
            for st in lens["source_tags"]:
                self.assertIn(st, vr.TAGS, f"{tag}: {st}")

    def test_declared_focus_parses_list_and_csv_forms(self):
        self.assertEqual(vr.declared_focus("---\nfocus: [seo, a11y]\n---\nx"), ["seo", "a11y"])
        self.assertEqual(vr.declared_focus("---\nfocus: seo, #perf\n---\nx"), ["seo", "perf"])
        self.assertEqual(vr.declared_focus("---\nfocus: []\n---\nx"), [])
        self.assertEqual(vr.declared_focus("no front matter\nfocus: seo"), [])

    def cli_focus_result(self, declaration, check, body=None):
        report = "---\n" + declaration + "\n---\n" + (
            body if body is not None else (FIX / "research-report-good.md").read_text()
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.md"
            path.write_text(report)
            return subprocess.run(
                [sys.executable, str(ROOT / "scripts/validate_report.py"),
                 check, str(path), "--offline"],
                capture_output=True, text=True, timeout=10,
                env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
            )

    def test_equivalent_focus_keys_enforce_missing_addenda(self):
        for key in ("focus ", "'focus'", '"focus"', "'focus' ", '"focus"\t'):
            with self.subTest(key=key):
                report = "---\n" + key + ": [security]\n---\n" + (
                    FIX / "research-report-good.md"
                ).read_text()
                self.assertEqual(vr.declared_focus(report), ["security"])
                self.assertIsNone(vr.focus_form_problem(report))
                self.assertEqual(vr.check_focus(report)[0], "FAIL")

    def test_equivalent_focus_keys_cannot_skip_cli_checks(self):
        for key in ("focus ", "'focus'", '"focus"', "'focus' ", '"focus"\t'):
            for check in ("structure", "all"):
                with self.subTest(key=key, check=check):
                    result = self.cli_focus_result(key + ": [security]", check)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn("Focus: FAIL", result.stdout)

    def test_equivalent_focus_keys_preserve_valid_reports(self):
        good = (FIX / "research-report-focus-good.md").read_text()
        body = good.split("---", 2)[2]
        for key in ("focus", "focus ", "'focus'", '"focus"'):
            for check in ("structure", "all"):
                with self.subTest(key=key, check=check):
                    result = self.cli_focus_result(
                        key + ": [security, devtools]", check, body
                    )
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertIn("Focus: PASS (security, devtools)", result.stdout)

    def test_multiline_quoted_focus_is_an_explicit_form_error(self):
        for declaration in (
            'focus: "none\n  #security"', "focus: 'none\n  #security'",
            'focus: "none', "focus: 'none",
            'focus:\n  - "none\n    #security"',
            "focus:\n  - 'none\n    #security'",
            'focus: ["none\n  #security"]',
            'focus:\n  - "none # still quoted\n    #security"',
        ):
            with self.subTest(declaration=declaration):
                report = "---\n" + declaration + "\n---\n" + (
                    FIX / "research-report-good.md"
                ).read_text()
                self.assertIsNotNone(vr.focus_form_problem(report))
                self.assertEqual(vr.check_focus(report)[0], "FAIL")

    def test_multiline_quoted_focus_cannot_skip_cli_checks(self):
        for declaration in (
            'focus: "none\n  #security"', "focus: 'none\n  #security'",
            'focus:\n  - "none\n    #security"',
            "focus:\n  - 'none\n    #security'",
        ):
            for check in ("structure", "all"):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli_focus_result(declaration, check)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn("Focus: FAIL", result.stdout)

    def test_balanced_quotes_and_comment_quotes_preserve_focus_contract(self):
        for declaration, expected in (
            ('focus: "none"', []), ("focus: 'security' # user's lens", ["security"]),
            ('focus: ["security", "#devtools"]', ["security", "devtools"]),
            ('focus: "none" # unclosed " comment', []),
            ('focus:\n  - "#security" # unclosed " comment', ["security"]),
            ('focus:\n  - # unclosed " comment\n  - security', ["security"]),
            ("focus: seo, #perf", ["seo", "perf"]),
        ):
            with self.subTest(declaration=declaration):
                report = "---\n" + declaration + "\n---\n"
                self.assertIsNone(vr.focus_form_problem(report))
                self.assertEqual(vr.declared_focus(report), expected)

    def test_indented_root_focus_still_requires_its_addendum(self):
        for declaration in (
            "  focus: [security]",
            "# root comment\n  focus: [security]",
            "  title: Report\n  'focus': [security]",
            '    "focus" :\n      - security\n    metadata:\n      owner: local',
        ):
            with self.subTest(declaration=declaration):
                report = "---\n" + declaration + "\n---\n" + (
                    FIX / "research-report-good.md"
                ).read_text()
                status, lines = vr.check_focus(report)
                self.assertEqual(status, "FAIL", lines)
                self.assertEqual(vr.declared_focus(report), ["security"])
                self.assertIsNone(vr.focus_form_problem(report))

    def test_indented_root_focus_cli_preserves_complete_and_missing_cases(self):
        complete = (FIX / "research-report-focus-good.md").read_text().split("---", 2)[2]
        for declaration in (
            "  focus: [security]",
            "# root comment\n  focus: [security]",
            "  title: Report\n  'focus': [security]",
            '    "focus" :\n      - security\n    metadata:\n      owner: local',
        ):
            for check in ("structure", "all"):
                for body, code, verdict in ((None, 1, "FAIL"), (complete, 0, "PASS (security)")):
                    with self.subTest(declaration=declaration, check=check, verdict=verdict):
                        result = self.cli_focus_result(declaration, check, body)
                        self.assertEqual(result.returncode, code, result.stdout)
                        self.assertIn("Focus: " + verdict, result.stdout)

    def test_nested_focus_keys_do_not_become_root_focus(self):
        for declaration in (
            "metadata:\n  focus: [security]",
            "  metadata:\n    focus: [security]\n  title: Report",
            "# root comment\n    metadata:\n      'focus': [security]",
            "description: |\n  focus: [security]",
        ):
            with self.subTest(declaration=declaration):
                report = "---\n" + declaration + "\n---\n"
                self.assertEqual(vr.declared_focus(report), [])
                self.assertIsNone(vr.focus_form_problem(report))
                self.assertEqual(vr.check_focus(report)[0], "PASS")
            for check in ("structure", "all"):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli_focus_result(declaration, check)
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertNotIn("Focus:", result.stdout)

    def test_comment_headers_share_quote_and_hashtag_interpretation(self):
        complete = (FIX / "research-report-focus-good.md").read_text().split("---", 2)[2]
        for header in ("#selected user's lenses", '#selected "unclosed comment',
                       "#none user's choice", '# selected "unclosed comment'):
            declaration = "focus: " + header + "\n  # skipped comment\n  - security"
            for body, expected in (((FIX / "research-report-good.md").read_text(), "FAIL"), (complete, "PASS")):
                with self.subTest(header=header, expected=expected):
                    report = "---\n" + declaration + "\n---\n" + body
                    status, lines = vr.check_focus(report)
                    self.assertEqual(status, expected, lines)
                    self.assertIsNone(vr.focus_form_problem(report))
                    self.assertEqual(vr.declared_focus(report), ["security"])

    def test_comment_headers_cli_preserves_complete_and_missing_cases(self):
        complete = (FIX / "research-report-focus-good.md").read_text().split("---", 2)[2]
        for header in ("#selected user's lenses", '#selected "unclosed comment'):
            for indent in ("", "  "):
                declaration = indent + "focus: " + header + "\n" + indent + "  - security"
                for check in ("structure", "all"):
                    for body, code, verdict in ((None, 1, "FAIL"), (complete, 0, "PASS (security)")):
                        with self.subTest(header=header, indent=indent, check=check, verdict=verdict):
                            result = self.cli_focus_result(declaration, check, body)
                            self.assertEqual(result.returncode, code, result.stdout)
                            self.assertIn("Focus: " + verdict, result.stdout)

    def test_fable_space_hashtags_never_pass_a_partial_addendum(self):
        seo_only = (FIX / "research-report-good.md").read_text() + "\n## SEO scorecard\nSearch evidence [GSC].\n"
        for declaration in ("focus: #seo #perf", "focus: #seo\t#perf", "  'focus': #seo #security"):
            report = "---\n" + declaration + "\n---\n" + seo_only
            with self.subTest(declaration=declaration):
                self.assertEqual(vr.check_focus(report)[0], "FAIL")
            for check in ("structure", "all"):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli_focus_result(declaration, check, seo_only)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn("Focus: FAIL", result.stdout)

    def test_fable_ambiguous_block_hashtags_fail_explicitly(self):
        for declaration in ("focus:\n  - #security", "focus:\n  - seo\n  - #security", "  'focus':\n    - #security"):
            report = "---\n" + declaration + "\n---\n" + (FIX / "research-report-good.md").read_text()
            with self.subTest(declaration=declaration):
                self.assertIsNotNone(vr.focus_form_problem(report))
                self.assertEqual(vr.check_focus(report)[0], "FAIL")
            for check in ("structure", "all"):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli_focus_result(declaration, check)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn("Focus: FAIL", result.stdout)

    def test_fable_comment_only_block_rows_remain_null(self):
        for declaration in ("focus:\n  - # user's note\n  - security", 'focus:\n  - # unclosed " comment\n  - security'):
            report = "---\n" + declaration + "\n---\n"
            with self.subTest(declaration=declaration):
                self.assertIsNone(vr.focus_form_problem(report))
                self.assertEqual(vr.declared_focus(report), ["security"])

    def test_fable_equivalent_depth_keys_require_process_records(self):
        for declaration in ("  depth: deep", "'depth': deep", '"depth" : deep', "  title: Report\n  'depth': deep", '  "depth": "deep"'):
            report = "---\n" + declaration + "\n---\n"
            with self.subTest(declaration=declaration):
                self.assertEqual(vr.declared_depth(report), "deep")
                self.assertEqual(vr.check_process(report)[0], "WARN")
            for check in ("structure", "all"):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli_focus_result(declaration, check)
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertIn("Process: WARN", result.stdout)
                    self.assertIn("Perspectives", result.stdout)
                    self.assertNotIn("not a --deep report", result.stdout)

    def test_fable_depth_nested_controls_and_complete_records(self):
        for declaration in ("metadata:\n  depth: deep", "  metadata:\n    'depth': deep", "description: |\n  depth: deep"):
            with self.subTest(declaration=declaration):
                self.assertEqual(vr.declared_depth("---\n" + declaration + "\n---\n"), "")
        body = (FIX / "research-report-good.md").read_text() + "\nPerspectives: 3 run\nAttribution: 8/8 supported\nInternal round: none relevant\n"
        for check in ("structure", "all"):
            with self.subTest(check=check):
                result = self.cli_focus_result("  'depth': deep", check, body)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn("Process: PASS", result.stdout)
                self.assertNotIn("not a --deep report", result.stdout)

    def test_fable_plain_apostrophes_do_not_open_quoted_scalars(self):
        for value in ("selected user's lenses", "#selected user's lenses", '#selected "unclosed comment'):
            with self.subTest(value=value):
                self.assertIsNone(vr.focus_value_parts(value)[1])
        for header in ("#selected user's lenses", '#selected "unclosed comment', "# selected user's lenses"):
            declaration = "focus: " + header
            report = "---\n" + declaration + "\n---\n"
            with self.subTest(header=header):
                self.assertIsNone(vr.focus_form_problem(report))
                self.assertEqual(vr.declared_focus(report), [])
            for check in ("structure", "all"):
                with self.subTest(header=header, check=check):
                    result = self.cli_focus_result(declaration, check)
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertNotIn("Focus: FAIL", result.stdout)

    def test_fable_duplicate_root_focus_keys_fail(self):
        for declaration in ("focus: none\nfocus: [security]", "focus: [security]\nfocus: none", "'focus': none\n\"focus\": [security]", "  focus: none\n  'focus': [security]"):
            report = "---\n" + declaration + "\n---\n"
            with self.subTest(declaration=declaration):
                self.assertIsNotNone(vr.focus_form_problem(report))
                self.assertEqual(vr.check_focus(report)[0], "FAIL")
            for check in ("structure", "all"):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli_focus_result(declaration, check)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn("Focus: FAIL", result.stdout)

    def test_fable_quoted_csv_and_nested_key_controls(self):
        complete = (FIX / "research-report-focus-good.md").read_text().split("---", 2)[2]
        for declaration in ("focus: #security, #devtools", "focus: [security, devtools]", "focus: security\nmetadata:\n  focus: none", 'focus: "#security" # user\'s comment'):
            report = "---\n" + declaration + "\n---\n" + complete
            with self.subTest(declaration=declaration):
                self.assertIsNone(vr.focus_form_problem(report))
                self.assertEqual(vr.check_focus(report)[0], "PASS")
            for check in ("structure", "all"):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli_focus_result(declaration, check, complete)
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertIn("Focus: PASS", result.stdout)

    def test_bundles_expand(self):
        self.assertEqual(vr.expand_focus(["ship-audit"]), ["security", "perf", "a11y"])
        self.assertEqual(vr.expand_focus(["security", "build-pick"]), ["security", "devtools"])

    def test_good_focus_fixture_passes(self):
        code, out = run(vr.main, ["structure", str(FIX / "research-report-focus-good.md")])
        self.assertEqual(code, 0, out)
        self.assertIn("Focus: PASS (security, devtools)", out)

    def test_bad_focus_fixture_fails_on_unknown_tag_and_missing_addendum(self):
        code, out = run(vr.main, ["structure", str(FIX / "research-report-focus-bad.md")])
        self.assertEqual(code, 1, out)
        self.assertIn("unknown focus tag 'sec'", out)
        self.assertIn("'SEO scorecard'", out)

    def test_missing_lens_sources_only_warns(self):
        text = (FIX / "research-report-focus-good.md").read_text()
        for st in ["OSV", "GHSA", "KEV"]:
            text = text.replace(st, "WS")
        status, lines = vr.check_focus(text)
        self.assertEqual(status, "WARN", lines)

    def test_unfocused_report_skips_focus_check(self):
        code, out = run(vr.main, ["structure", str(FIX / "research-report-good.md")])
        self.assertEqual(code, 0, out)
        self.assertNotIn("Focus:", out)

    def test_lens_authorities_rank_official(self):
        auth = vr.lens_authorities(["security", "ui-ux"], MANIFEST)
        self.assertEqual(vr.classify_url("https://owasp.org/Top10/2025/", auth), "official")
        self.assertEqual(vr.classify_url("https://www.nngroup.com/articles/x/", auth), "official")
        self.assertEqual(vr.classify_url("https://owasp.org.evil.example/", auth), "unknown")

    def test_only_active_lens_authorities_gain_trust(self):
        # Review finding 2026-10-02: every lens's authorities ranked official for every report.
        self.assertEqual(vr.classify_url("https://owasp.org/Top10/2025/"), "unknown")
        self.assertEqual(
            vr.classify_url("https://owasp.org/Top10/2025/", vr.lens_authorities(["seo"], MANIFEST)),
            "unknown",
        )
        report = "---\nfocus: security\n---\nSee https://owasp.org/Top10/2025/ [OSV]\n"
        self.assertIn("official", "\n".join(vr.check_sources(report)[1]))

    def test_focus_none_means_no_focus(self):
        for value in ["none", "null", "~", "[]", "[none]"]:
            self.assertEqual(vr.declared_focus(f"---\nfocus: {value}\n---\nbody\n"), [], value)


class ProcessCheckTest(unittest.TestCase):
    DEEP = "---\ndepth: deep\n---\n"

    def test_shallow_report_is_not_checked(self):
        self.assertEqual(vr.check_process("---\ndepth: default\n---\nx")[0], "PASS")

    def test_deep_report_without_records_warns(self):
        status, lines = vr.check_process(self.DEEP + "body")
        self.assertEqual(status, "WARN")
        joined = "\n".join(lines)
        self.assertIn("Perspectives", joined)
        self.assertIn("Attribution", joined)
        self.assertIn("Internal round", joined)

    def test_deep_report_with_records_passes(self):
        text = self.DEEP + ("|- Internal round: slack, fireflies\n"
                            "|- Perspectives: 3 run | 3 with findings\n"
                            "|- Attribution: 8/8 spot-checked claims supported\n")
        self.assertEqual(vr.check_process(text)[0], "PASS")

    def test_partial_attribution_warns(self):
        text = self.DEEP + ("|- Internal round: none relevant\n|- Perspectives: 3 run\n"
                            "|- Attribution: 6/8 supported\n")
        status, lines = vr.check_process(text)
        self.assertEqual(status, "WARN")
        self.assertIn("6/8", "\n".join(lines))

    def test_process_warn_does_not_fail_structure(self):
        code, out = run(vr.main, ["structure", str(FIX / "research-report-focus-good.md")])
        self.assertEqual(code, 0, out)


class FocusCheckTest(unittest.TestCase):
    def test_repo_lint_passes(self):
        self.assertEqual(fc.lint(str(ROOT)), [])

    def test_every_tag_has_a_lens_file_with_its_addendum(self):
        for tag, lens in MANIFEST["tags"].items():
            text = (ROOT / "focus" / f"{tag}.md").read_text()
            self.assertIn(lens["addendum"], text)

    def test_lint_catches_a_broken_lens(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for sub in ("focus", "references", "scripts", "docs"):
                (root / sub).mkdir()
            for f in (ROOT / "focus").iterdir():
                (root / "focus" / f.name).write_text(f.read_text())
            reg = json.loads((ROOT / "references/tool-registry.json").read_text())
            reg["osv"]["focus"] = ["devtools"]          # lens and registry disagree
            del reg["spyfu"]["fallback"]                 # paid tool with no free fallback
            (root / "references/tool-registry.json").write_text(json.dumps(reg))
            text = (root / "focus/a11y.md").read_text().replace("## Freshness", "## Fresh")
            (root / "focus/a11y.md").write_text(text)
            errors = "\n".join(fc.lint(str(root)))
            self.assertIn("tool 'osv' lists focus", errors)
            self.assertIn("spyfu", errors)
            self.assertIn("a11y.md: missing '## Freshness'", errors)

    def test_suggest_matches_triggers(self):
        tags = [t for t, _ in fc.suggest("is our checkout vulnerable to a CVE in the auth library?", MANIFEST)]
        self.assertIn("security", tags)
        self.assertIn("devtools", tags)
        self.assertLessEqual(len(tags), MANIFEST["limits"]["max_tags"])
        self.assertEqual(fc.suggest("a poem about autumn leaves", MANIFEST), [])

    def test_dialer_topic_suggests_comms(self):
        # Regression from the first live v3 run (2026-10-01): no lens fired on a dialer topic.
        topic = "integrated RingCentral dialer for our CRM with power dialing, SMS and call recording"
        self.assertIn("comms", [t for t, _ in fc.suggest(topic, MANIFEST)])
        comms = vr.lens_authorities(["comms"], MANIFEST)
        self.assertEqual(vr.classify_url("https://developers.ringcentral.com/guide/voice", comms), "official")
        self.assertEqual(
            vr.classify_url("https://vercel.com/docs/tracing", vr.lens_authorities(["data-infra"], MANIFEST)),
            "official",
        )

    def test_expand_reports_unknown_and_bundles(self):
        tags, unknown = fc.expand(["#launch", "sec"], MANIFEST)
        self.assertEqual(tags, ["seo", "perf", "a11y", "content"])
        self.assertEqual(unknown, ["sec"])

    def test_plan_cli(self):
        code, out = run(fc.main, ["plan", "seo"])
        self.assertEqual(code, 0)
        self.assertIn("SEO scorecard", out)
        self.assertIn("[DFS] DataForSEO", out)
        self.assertEqual(run(fc.main, ["plan", "nope"])[0], 1)

    def test_probe_never_prints_key_values(self):
        os.environ["SPYFU_API_KEY"] = "sekret-value-123"
        try:
            code, out = run(fc.main, ["probe", "seo"])
        finally:
            del os.environ["SPYFU_API_KEY"]
        self.assertEqual(code, 0)
        self.assertIn("spyfu: key set (SPYFU_API_KEY)", out)
        self.assertNotIn("sekret-value-123", out)

    def test_probe_free_skips_paid(self):
        code, out = run(fc.main, ["probe", "seo", "--free"])
        self.assertIn("dataforseo: skipped (--free)", out)

    def test_docs_table_in_sync(self):
        code, out = run(fc.main, ["docs"])
        self.assertEqual(code, 0, out)



class FallbackChainTest(unittest.TestCase):
    def test_paid_chain_must_end_at_a_non_paid_tool(self):
        reg = {
            "a": {"cost": "paid", "fallback": "b"},
            "b": {"cost": "paid", "fallback": "c"},
            "c": {"cost": "free"},
            "loop1": {"cost": "paid", "fallback": "loop2"},
            "loop2": {"cost": "paid", "fallback": "loop1"},
            "dead": {"cost": "paid", "fallback": "b2"},
            "b2": {"cost": "paid"},
        }
        self.assertTrue(fc.reaches_free("a", reg))
        self.assertFalse(fc.reaches_free("loop1", reg))
        self.assertFalse(fc.reaches_free("dead", reg))

    def test_plan_reads_lens_files_from_the_given_root(self):
        manifest = {"tags": {"zz": {"title": "Z", "addendum": "Z table"}}}
        with tempfile.TemporaryDirectory() as d:
            Path(d, "zz.md").write_text("no tools here\n", encoding="utf-8")
            self.assertIn("zz: Z", fc.plan(["zz"], manifest, {}, d))


class CommandMirrorTest(unittest.TestCase):
    def test_command_lists_every_tag_addendum_and_bundle(self):
        # Review finding 2026-10-02: the command's tag table is a hand copy of tags.json.
        text = (Path(__file__).resolve().parent.parent / "commands" / "research-stack.md").read_text()
        for tag, lens in MANIFEST["tags"].items():
            self.assertRegex(text, rf"\| `{re.escape(tag)}` +\|.*\| {re.escape(lens['addendum'])} *\|", tag)
        for bundle, members in MANIFEST["bundles"].items():
            self.assertIn(f"`#{bundle}` ({', '.join(members)})", text, bundle)

    def test_block_list_focus_is_read(self):
        report = "---\nfocus:\n  - seo\n  - a11y\ndepth: deep\n---\nbody\n"
        self.assertEqual(vr.declared_focus(report), ["seo", "a11y"])

if __name__ == "__main__":
    unittest.main()
