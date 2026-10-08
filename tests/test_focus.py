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
    def test_mixed_root_indentation_cannot_grant_lens_authority(self):
        for first, lower in ((2, 0), (4, 2)):
            report = ('---\n' + ' ' * first + 'title: Report\n' +
                      ' ' * lower + 'metadata:\n' + ' ' * first +
                      'focus: [security]\n---\nhttps://owasp.org/Top10/2025/ [OSV]\n')
            with self.subTest(first=first, lower=lower):
                self.assertIsNotNone(vr.root_mapping_problem(report))
                self.assertEqual(vr.declared_focus(report), [])
                self.assertEqual(vr.check_sources(report)[0], 'FAIL')

    def test_invalid_metadata_all_still_prints_fail_verdict(self):
        result = self.cli_focus_result('focus: [unknown-tag]', 'all')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Verdict: FAIL', result.stdout)

    def test_large_quote_and_comma_headers_finish_within_cli_bound(self):
        for value in ('x"' * 50000, ',' * 100000 + 'unknown-tag'):
            with self.subTest(kind=value[:2]):
                try:
                    result = self.cli_focus_result('focus: ' + value, 'all')
                except subprocess.TimeoutExpired:
                    self.fail('large header stalled report validation')
                self.assertEqual(result.returncode, 1, result.stdout)

    def test_malformed_property_prefixes_return_without_backtracking(self):
        for count in (40, 4000):
            for marker in ('!', '&'):
                with self.subTest(count=count, marker=marker):
                    try:
                        result = self.cli_focus_result(
                            'focus: ' + marker * count + ' x "', 'all')
                    except subprocess.TimeoutExpired:
                        self.fail('malformed properties stalled report validation')
                    self.assertEqual(result.returncode, 1, result.stdout)

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

    def test_astra_mixed_csv_hashtags_cannot_skip_security(self):
        partial = (FIX / "research-report-good.md").read_text() + (
            "\n## SEO scorecard\nSearch evidence [GSC].\n"
            "\n## Performance budget\nPerformance evidence [LH].\n"
        )
        for declaration in ("focus: seo, #perf #security", "focus: seo, #perf\t#security", "  'focus': 'seo', #perf #security"):
            report = "---\n" + declaration + "\n---\n" + partial
            with self.subTest(declaration=declaration):
                self.assertIsNotNone(vr.focus_form_problem(report))
                self.assertEqual(vr.check_focus(report)[0], "FAIL")
            for check in ("structure", "all"):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli_focus_result(declaration, check, partial)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn("Focus: FAIL", result.stdout)

    def test_astra_hashtag_guard_respects_quotes_commas_and_comments(self):
        complete = (FIX / "research-report-focus-good.md").read_text().split("---", 2)[2]
        for declaration in (
            "focus: security, #devtools",
            "focus: security, #devtools # a comment with #perf #seo",
            'focus: "security" # a comment with #perf #seo',
            "focus: [security, '#devtools'] # #perf #seo",
        ):
            report = "---\n" + declaration + "\n---\n" + complete
            with self.subTest(declaration=declaration):
                self.assertIsNone(vr.focus_form_problem(report))
                self.assertEqual(vr.check_focus(report)[0], "PASS")
            for check in ("structure", "all"):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli_focus_result(declaration, check, complete)
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertIn("Focus: PASS", result.stdout)
        self.assertIsNone(vr.focus_form_problem('---\nfocus: "#perf #security"\n---\n'))
        self.assertEqual(vr.check_focus('---\nfocus: "#perf #security"\n---\n')[0], "FAIL")

    def test_astra_next_line_depth_requires_process_records(self):
        for declaration in (
            "depth:\n  deep",
            "depth: # user's setting\n  # depth comment\n  deep",
            "  title: Report\n  'depth':\n    'deep'",
            '"depth":\n  "deep"',
        ):
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
                    self.assertIn("Attribution", result.stdout)
                    self.assertIn("Internal round", result.stdout)
                    self.assertNotIn("not a --deep report", result.stdout)

    def test_astra_next_line_depth_keeps_complete_and_nested_controls(self):
        complete = (FIX / "research-report-good.md").read_text() + (
            "\nPerspectives: 3 run\nAttribution: 8/8 supported\nInternal round: none relevant\n"
        )
        for check in ("structure", "all"):
            with self.subTest(check=check):
                result = self.cli_focus_result("depth:\n  deep", check, complete)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn("Process: PASS", result.stdout)
                self.assertNotIn("not a --deep report", result.stdout)
        for declaration in (
            "depth:\nother: deep", "metadata:\n  depth:\n    deep",
            "depth:\n  # deep is only a comment\nother: default",
            "depth:\n  details:\n    level: deep", "depth:\n  - deep",
        ):
            with self.subTest(declaration=declaration):
                self.assertNotEqual(vr.declared_depth("---\n" + declaration + "\n---\n"), "deep")

    def final143_focus_body(self, security=False):
        body = (FIX / "research-report-good.md").read_text() + (
            "\n## SEO scorecard\nSearch evidence [GSC].\n"
            "\n## Performance budget\nPerformance evidence [LH].\n"
        )
        if security:
            body += "\n## Threat and advisory table\nSecurity evidence [OSV].\n"
        return body

    def test_final143_header_csv_separator_matrix(self):
        for value in ("#seo,#security", "#seo , #security", "#seo\t,\t#security", "seo , #security", "'#seo', '#security'", '["#seo" , #security]'):
            for key in ("focus", "  'focus'"):
                declaration = key + ": " + value
                report = "---\n" + declaration + "\n---\n"
                with self.subTest(value=value, key=key):
                    self.assertIsNone(vr.focus_form_problem(report))
                    self.assertEqual(vr.declared_focus(report), ["seo", "security"])
                for complete in (False, True):
                    for check in ("focus", "structure", "all"):
                        with self.subTest(value=value, key=key, complete=complete, check=check):
                            result = self.cli_focus_result(declaration, check, self.final143_focus_body(complete))
                            self.assertEqual(result.returncode, 0 if complete else 1, result.stdout)
                            self.assertIn("Focus: PASS" if complete else "Focus: FAIL", result.stdout)

    def test_final143_header_and_block_share_ambiguity(self):
        for value in ("seo, #perf #security", "seo , #perf\t#security", "seo, #perf #security # note", "seo, #perf #security, devtools"):
            self.assertTrue(vr.scan_focus_value(value)[2])
            for prefix in ("focus: ", "focus:\n  - "):
                declaration = prefix + value
                with self.subTest(value=value, prefix=prefix):
                    self.assertIsNotNone(vr.focus_form_problem("---\n" + declaration + "\n---\n"))
                for check in ("focus", "structure", "all"):
                    with self.subTest(value=value, prefix=prefix, check=check):
                        result = self.cli_focus_result(declaration, check, self.final143_focus_body())
                        self.assertEqual(result.returncode, 1, result.stdout)
                        self.assertIn("Focus: FAIL", result.stdout)

    def test_final143_valid_header_and_block_csv_share_checks(self):
        for value in ("seo, #perf, #security", "seo , '#perf' , \"#security\"", "seo, perf, security # note with #other #tags"):
            for prefix in ("focus: ", "focus:\n  - "):
                declaration = prefix + value
                report = "---\n" + declaration + "\n---\n"
                with self.subTest(value=value, prefix=prefix):
                    self.assertIsNone(vr.focus_form_problem(report))
                    self.assertEqual(vr.declared_focus(report), ["seo", "perf", "security"])
                for complete in (False, True):
                    for check in ("focus", "structure", "all"):
                        with self.subTest(value=value, prefix=prefix, complete=complete, check=check):
                            result = self.cli_focus_result(declaration, check, self.final143_focus_body(complete))
                            self.assertEqual(result.returncode, 0 if complete else 1, result.stdout)
                            self.assertIn("Focus: PASS" if complete else "Focus: FAIL", result.stdout)

    def test_final143_focus_quote_comment_unknown_and_plain_controls(self):
        for prefix in ("focus: ", "focus:\n  - "):
            for value in ("'security' # comment with #perf #seo", '"#security" # user\'s note'):
                declaration = prefix + value
                report = "---\n" + declaration + "\n---\n" + self.final143_focus_body(True)
                with self.subTest(prefix=prefix, value=value):
                    self.assertIsNone(vr.focus_form_problem(report))
                    self.assertEqual(vr.declared_focus(report), ["security"])
                    self.assertEqual(vr.check_focus(report)[0], "PASS")
            for value in ('"security', "'security", '["security'):
                declaration = prefix + value
                with self.subTest(prefix=prefix, value=value):
                    self.assertIsNotNone(vr.scan_focus_value(value)[1])
                    self.assertEqual(vr.check_focus("---\n" + declaration + "\n---\n" + self.final143_focus_body(True))[0], "FAIL")
        for declaration in ("focus: #unknown", "focus:\n  - #unknown", "focus:\n  - '#unknown'", "focus: [unknown]", "focus:\n  - [security]"):
            for check in ("focus", "structure", "all"):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli_focus_result(declaration, check, self.final143_focus_body(True))
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn("Focus: FAIL", result.stdout)
        for declaration in ("focus: none", "focus: #selected user's lenses", "focus: # selected lenses", "focus:\n  - # user's note\n  - security"):
            for check in ("focus", "structure", "all"):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli_focus_result(declaration, check, self.final143_focus_body(True))
                    self.assertEqual(result.returncode, 0, result.stdout)

    def test_final143_depth_comments_use_yaml_semantics(self):
        for header in ("#selected", "# selected", "#selected user's settings", "#seo , #security", "#perf #security", "#"):
            for key, indent in (("depth", "  "), ("  'depth'", "    ")):
                declaration = key + ": " + header + "\n" + indent + "deep"
                report = "---\n" + declaration + "\n---\n"
                with self.subTest(header=header, key=key):
                    self.assertEqual(vr.declared_depth(report), "deep")
                    self.assertEqual(vr.check_process(report)[0], "WARN")
                for check in ("structure", "all"):
                    with self.subTest(header=header, key=key, check=check):
                        result = self.cli_focus_result(declaration, check)
                        self.assertEqual(result.returncode, 0, result.stdout)
                        self.assertIn("Process: WARN", result.stdout)
                        self.assertIn("Perspectives", result.stdout)
                        self.assertIn("Attribution", result.stdout)
                        self.assertIn("Internal round", result.stdout)

    def test_final143_depth_literal_and_nested_controls(self):
        for declaration, expected in (
            ('depth: "#selected"', "#selected"), ("depth: deep#selected", "deep#selected"),
            ("depth: default #selected", "default"), ("depth: deep #selected", "deep"),
            ("depth: #selected\nnext: deep", ""), ("metadata:\n  depth: #selected\n    deep", ""),
            ("depth: #selected\n  - deep", ""), ("depth: #selected\n  mapping:\n    value: deep", ""),
        ):
            with self.subTest(declaration=declaration):
                self.assertEqual(vr.declared_depth("---\n" + declaration + "\n---\n"), expected)
        complete = self.final143_focus_body() + "\nPerspectives: 3 run\nAttribution: 8/8 supported\nInternal round: none relevant\n"
        for check in ("structure", "all"):
            with self.subTest(check=check):
                result = self.cli_focus_result("depth: #selected\n  deep", check, complete)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn("Process: PASS", result.stdout)
                self.assertNotIn("not a --deep report", result.stdout)

    FINAL149_CALLERS = ("focus", "structure", "process", "sources", "citations", "all")

    def final149_cli(self, declaration, check, body=None):
        body = body if body is not None else self.final143_focus_body(True)
        if check == "citations":
            body = vr.URL_RE.sub("offline citation omitted", body)
        return self.cli_focus_result(declaration, check, body)

    def test_final149_quoted_content_never_collapses_into_none(self):
        values = ("'none'' #security'", "'none'''", "'null'' #security'", '"none\\\" #security"', "'none,none'", '"none,none"', "['none'' #security']")
        for value in values:
            for prefix in ("focus: ", "focus:\n  - "):
                declaration = prefix + value
                report = "---\n" + declaration + "\n---\n" + self.final143_focus_body(True)
                with self.subTest(value=value, prefix=prefix):
                    self.assertTrue(vr.declared_focus(report))
                    self.assertEqual(vr.check_focus(report)[0], "FAIL")
                for check in self.FINAL149_CALLERS:
                    with self.subTest(value=value, prefix=prefix, check=check):
                        result = self.final149_cli(declaration, check)
                        self.assertEqual(result.returncode, 1, result.stdout)
                        self.assertIn("FAIL", result.stdout)

    def test_final149_unsupported_root_mapping_syntax_fails_all_callers(self):
        for declaration in (
            "{focus: [security]}", "  {depth: deep}", "{focus: [security], depth: deep}",
            "? focus\n: [security]", "? 'focus'\n: [security]", "? depth\n: deep",
            "<<: {focus: [security]}", '"fo\\u0063us": [security]', '"de\\u0070th": deep',
            "[focus, security]", "- focus: [security]", "plain root scalar",
        ):
            report = "---\n" + declaration + "\n---\n"
            with self.subTest(declaration=declaration):
                self.assertIsNotNone(vr.focus_form_problem(report))
                self.assertEqual(vr.check_focus(report)[0], "FAIL")
                self.assertEqual(vr.check_process(report)[0], "FAIL")
            for check in self.FINAL149_CALLERS:
                with self.subTest(declaration=declaration, check=check):
                    result = self.final149_cli(declaration, check)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn("FAIL", result.stdout)

    def test_final149_source_authority_requires_validated_focus(self):
        for declaration in (
            "focus:\n  - security\n    extra", "focus: [security]\n  continued",
            "focus: none\nfocus: [security]", "focus: seo, #perf #security",
            "focus: 'none'' #security'", "{focus: [security]}",
        ):
            body = "https://owasp.org/Top10/2025/ [OSV]\n"
            report = "---\n" + declaration + "\n---\n" + body
            with self.subTest(declaration=declaration):
                status, lines = vr.check_sources(report)
                self.assertEqual(status, "FAIL", lines)
                self.assertNotIn("official (9/10)", "\n".join(lines))
            with self.subTest(declaration=declaration, check="sources"):
                result = self.final149_cli(declaration, "sources", body)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertNotIn("official (9/10)", result.stdout)
        valid = "---\nfocus: security\n---\nhttps://owasp.org/Top10/2025/ [OSV]\n"
        self.assertIn("official (9/10)", "\n".join(vr.check_sources(valid)[1]))
        self.assertNotIn("official (9/10)", "\n".join(vr.check_sources("https://owasp.org/Top10/2025/")[1]))

    def test_final149_direct_checks_reject_unsupported_metadata(self):
        report = "---\n{depth: deep, focus: [security]}\n---\n" + self.final143_focus_body(True)
        for check in (vr.check_focus, vr.check_structure, vr.check_process, vr.check_sources):
            with self.subTest(check=check.__name__):
                self.assertEqual(check(report)[0], "FAIL")

    def test_final149_supported_and_absent_metadata_remain_valid(self):
        for declaration in (
            "", "title: Report", "title: Report\nmetadata: {focus: [security], depth: deep}",
            "title: Report\nmetadata:\n  focus: [security]\n  depth: deep",
            "title: Report\nauthors:\n- local\nnotes: |\n  ? focus\n  : [security]",
            "'title': Report\nfocus: none\ndepth: default",
            "  title: Report\n  focus: [security]\n  depth: default",
            "focus:\n- security\ndepth: default",
        ):
            for check in self.FINAL149_CALLERS:
                with self.subTest(declaration=declaration, check=check):
                    result = self.final149_cli(declaration, check)
                    self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(vr.check_focus("An ordinary report without front matter.")[0], "PASS")

    def test_final149_quoted_escape_controls_preserve_scalar_identity(self):
        for value in ("'none'", '"none"', '"\\u006eone"'):
            report = "---\nfocus: " + value + "\n---\n"
            with self.subTest(value=value):
                self.assertEqual(vr.declared_focus(report), [])
                self.assertEqual(vr.check_focus(report)[0], "PASS")
        for value in ("'security'", '"#security"', '"secu\\u0072ity"'):
            report = "---\nfocus: " + value + "\n---\n" + self.final143_focus_body(True)
            with self.subTest(value=value):
                self.assertEqual(vr.declared_focus(report), ["security"])
                self.assertEqual(vr.check_focus(report)[0], "PASS")
        self.assertEqual(vr.declared_depth('---\ndepth: "de\\u0065p"\n---\n'), "deep")

    def test_final149_unsupported_depth_forms_never_claim_shallow(self):
        for declaration in (
            "depth: *selected", "depth: &selected deep", "depth: |\n  deep",
            "depth:\n  [deep]", "depth: default\ndepth: deep", "depth: {level: deep}",
        ):
            for check in self.FINAL149_CALLERS:
                with self.subTest(declaration=declaration, check=check):
                    result = self.final149_cli(declaration, check)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn("FAIL", result.stdout)
                    self.assertNotIn("not a --deep report", result.stdout)

    def final157_cli(self, report, check):
        if check == "citations":
            report = vr.URL_RE.sub("offline citation omitted", report)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.md"
            path.write_bytes(report.encode("utf-8"))
            return subprocess.run(
                [sys.executable, str(ROOT / "scripts/validate_report.py"), check, str(path), "--offline"],
                capture_output=True, text=True, timeout=10,
                env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
            )

    def test_final157_depth_sequences_fail_direct_and_all_cli(self):
        for declaration in (
            "depth:\n- deep", "depth:\n  - deep", "depth:\n- 'deep'",
            'depth: #selected\n- "deep"', "  'depth':\n  - deep",
            "depth:\n- default", "depth:\n- none", "depth:\n- # comment\n- deep",
            "depth: default\n- deep", "depth:\n  deep\n- extra",
        ):
            report = "---\n" + declaration + "\n---\n" + self.final143_focus_body(True)
            for checker in (vr.check_focus, vr.check_structure, vr.check_process, vr.check_sources):
                with self.subTest(declaration=declaration, checker=checker.__name__):
                    self.assertEqual(checker(report)[0], "FAIL")
            for check in self.FINAL149_CALLERS:
                with self.subTest(declaration=declaration, check=check):
                    result = self.final157_cli(report, check)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn("FAIL", result.stdout)
                    self.assertNotIn("not a --deep report", result.stdout)

    def test_final157_initial_bom_preserves_all_metadata_checks(self):
        for complete in (False, True):
            report = "---\nfocus: [security]\ndepth: deep\n---\n" + self.final143_focus_body(complete)
            bom_report = "\ufeff" + report
            with self.subTest(complete=complete):
                self.assertEqual(vr.declared_focus(bom_report), ["security"])
                self.assertEqual(vr.declared_depth(bom_report), "deep")
                self.assertEqual(vr.validated_metadata(bom_report), vr.validated_metadata(report))
            for checker in (vr.check_focus, vr.check_structure, vr.check_process, vr.check_sources):
                with self.subTest(complete=complete, checker=checker.__name__):
                    self.assertEqual(checker(bom_report), checker(report))
            for check in self.FINAL149_CALLERS:
                with self.subTest(complete=complete, check=check):
                    plain = self.final157_cli(report, check)
                    bom = self.final157_cli(bom_report, check)
                    self.assertEqual((bom.returncode, bom.stdout), (plain.returncode, plain.stdout))

    def test_final157_misplaced_or_repeated_bom_is_an_explicit_gap(self):
        for prefix in (" \ufeff", "\n\ufeff", "\t\ufeff", "\ufeff\ufeff", "\ufeff \ufeff", " \ufeff\ufeff"):
            report = prefix + "---\nfocus: [security]\ndepth: deep\n---\n" + self.final143_focus_body(True)
            for checker in (vr.check_focus, vr.check_structure, vr.check_process, vr.check_sources):
                with self.subTest(prefix=repr(prefix), checker=checker.__name__):
                    self.assertEqual(checker(report)[0], "FAIL")
            for check in self.FINAL149_CALLERS:
                with self.subTest(prefix=repr(prefix), check=check):
                    result = self.final157_cli(report, check)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn("FAIL", result.stdout)

    def test_final157_metadata_delimiter_controls(self):
        for opening, closing in (("---\n", ""), ("---\n", "--\n"), ("---\n", "--- extra\n"), ("---\n", "\ufeff---\n"), ("--- # metadata\n", "---\n")):
            report = "\ufeff" + opening + "focus: [security]\ndepth: deep\n" + closing + self.final143_focus_body(True)
            for checker in (vr.check_focus, vr.check_structure, vr.check_process, vr.check_sources):
                with self.subTest(opening=opening, closing=closing, checker=checker.__name__):
                    self.assertEqual(checker(report)[0], "FAIL")
            for check in self.FINAL149_CALLERS:
                with self.subTest(opening=opening, closing=closing, check=check):
                    result = self.final157_cli(report, check)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn("FAIL", result.stdout)
        for prefix, newline in (("", "\n"), ("\ufeff", "\n"), ("\ufeff", "\r\n"), ("\ufeff \n", "\n")):
            report = prefix + newline.join(("---", "focus: [security]", "depth: default", "---", "")) + self.final143_focus_body(True)
            with self.subTest(prefix=repr(prefix), newline=repr(newline)):
                self.assertEqual(vr.validated_metadata(report)["focus"], ["security"])
                self.assertEqual(vr.declared_depth(report), "default")
            for check in self.FINAL149_CALLERS:
                with self.subTest(prefix=repr(prefix), newline=repr(newline), check=check):
                    result = self.final157_cli(report, check)
                    self.assertEqual(result.returncode, 0, result.stdout)

    def test_final157_supported_depth_and_unrelated_sequences_remain_valid(self):
        complete = self.final143_focus_body(True) + "\nPerspectives: 3 run\nAttribution: 8/8 supported\nInternal round: none relevant\n"
        for declaration, expected in (
            ("title: Report", ""), ("depth:", ""), ("depth: default", "default"),
            ("depth: deep", "deep"), ("'depth': 'deep'", "deep"), ('depth:\n  "deep"', "deep"),
            ("depth:\nnext:\n- deep", ""), ("depth: default\nnext:\n- deep", "default"),
            ("metadata:\n  depth:\n  - deep", ""), ("focus:\n- security\ndepth: default", "default"),
        ):
            report = "\ufeff---\n" + declaration + "\n---\n" + complete
            with self.subTest(declaration=declaration):
                self.assertEqual(vr.declared_depth(report), expected)
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(report)))
            for check in self.FINAL149_CALLERS:
                with self.subTest(declaration=declaration, check=check):
                    result = self.final157_cli(report, check)
                    self.assertEqual(result.returncode, 0, result.stdout)


    FINAL164_TABBED = (
        "\tfocus: [security]\n\tdepth: deep", " \tfocus: [security]", "\t depth: deep",
        "title: Report\n\tfocus: content", "title: Report\n \tdepth: deep",
        "  title: Report\n  \tfocus: content", "\t'focus': content\n\t'depth': deep",
        ' \t"focus": [content]\n \t"depth": deep', "focus:\n\t- content",
        "metadata:\n\tfocus: content", "description: |\n\tfocus: content",
    )
    FINAL164_FOREIGN_QUOTES = (
        'title: "Notes\nfocus: content #"', "title: 'Notes\nfocus: content #'",
        'title: "Notes\ndepth: deep #"', "title: 'Notes\ndepth: deep #'",
        '  "title": "Notes\n  focus: content #"', 'title: "Notes # still quoted\nfocus: content #"',
        "title: 'User''s notes\nfocus: content #'", 'title: "Notes \\" still quoted\nfocus: content #"',
        'title:\n  "Notes\nfocus: content #"', 'metadata:\n  note: "Notes\nfocus: content #"',
        'authors:\n  - "Notes\nfocus: content #"', "authors:\n- 'Notes\nfocus: content #'",
        'title: ["Notes\nfocus: content #"]', 'title: {note: "Notes\nfocus: content #"}',
        'title: {note: "Notes }\nfocus: content #"}',
    )

    def final164_direct_assertions(self, declaration, body):
        report = "---\n" + declaration + "\n---\n" + body
        with self.subTest(declaration=declaration, checker="validated_metadata"):
            metadata = vr.validated_metadata(report)
            self.assertIsNotNone(vr.metadata_problem(metadata))
            self.assertEqual(metadata["focus"], [])
            self.assertEqual(metadata["depth"], "")
        for checker in (vr.check_focus, vr.check_structure, vr.check_process, vr.check_sources):
            with self.subTest(declaration=declaration, checker=checker.__name__):
                status, lines = checker(report)
                self.assertEqual(status, "FAIL", lines)
                self.assertNotIn("official (9/10)", "\n".join(lines))
        with self.subTest(declaration=declaration, checker="direct_extractors"):
            self.assertEqual(vr.declared_focus(report), [])
            self.assertEqual(vr.declared_depth(report), "")
        with self.subTest(declaration=declaration, checker="check_citations"):
            calls = []
            def fetch(*args, **kwargs):
                calls.append(True)
                return 200
            status, lines = vr.check_citations(report, fetch=fetch)
            self.assertEqual(status, "FAIL", lines)
            self.assertFalse(calls)
        for check in self.FINAL149_CALLERS:
            with self.subTest(declaration=declaration, check=check):
                result = self.final157_cli(report, check)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("FAIL", result.stdout)
                self.assertNotIn("official (9/10)", result.stdout)
                self.assertNotIn("not a --deep report", result.stdout)

    def test_final164_tabbed_metadata_is_explicitly_unsupported(self):
        for declaration in self.FINAL164_TABBED:
            for complete in (False, True):
                self.final164_direct_assertions(declaration, self.final143_focus_body(complete))

    def test_final164_multiline_foreign_quotes_cannot_activate_metadata(self):
        for declaration in self.FINAL164_FOREIGN_QUOTES:
            self.final164_direct_assertions(declaration, self.final143_focus_body(True) + "\nhttps://youtube.com/example [YT]\n")

    def test_final164_supported_foreign_values_and_comments_remain_valid(self):
        controls = (
            "title: Notes\nfocus: none\ndepth: default",
            "title: It's fine\nfocus: none", 'title: Notes "unclosed plain text\nfocus: none',
            'title: "focus: content # depth: deep"\nfocus: none',
            "title: 'User''s # notes' # unmatched ' comment\nfocus: none",
            'title: "Notes \\" quoted" # unmatched " comment\nfocus: none',
            'title: "Notes\tvalues"\nfocus: none',
            'metadata: {note: "focus: content # depth: deep"}\nfocus: none',
            'metadata: ["focus: content # depth: deep"]\nfocus: none',
            'description: |\n  "Notes\n  focus: content #"\nfocus: none',
            'description: >-\n  "Notes\n  depth: deep #"\ndepth: default',
            'description: |\n  \t"Notes\n  focus: content #"\nfocus: none',
            "\t# ignored comment\ntitle: Report\nfocus: none",
            "metadata:\n  title: 'Notes'\n  focus: content\nfocus: none",
            "authors:\n- 'Notes'\nfocus: none", "  title: 'Notes'\n  focus: none",
            "focus:\t[security, devtools]\ndepth:\tdefault",
        )
        for declaration in controls:
            report = "---\n" + declaration + "\n---\n" + self.final143_focus_body(True) + "\n## " + MANIFEST["tags"]["devtools"]["addendum"] + "\nFixture library decision.\n"
            with self.subTest(declaration=declaration):
                metadata = vr.validated_metadata(report)
                self.assertIsNone(vr.metadata_problem(metadata))
                self.assertEqual(metadata["focus"], ["security", "devtools"] if declaration.startswith("focus:\t") else [])
            for check in self.FINAL149_CALLERS:
                with self.subTest(declaration=declaration, check=check):
                    result = self.final157_cli(report, check)
                    self.assertEqual(result.returncode, 0, result.stdout)

    def test_final164_authority_requires_an_actual_root_focus(self):
        body = "https://youtube.com/example [YT]\n"
        for declaration, official in (
            ('title: "focus: content"', False), ('title: {note: "focus: content"}', False),
            ("title: 'Notes'\nfocus: content", True), ("  title: Notes\n  focus: content", True),
        ):
            report = "---\n" + declaration + "\n---\n" + body
            with self.subTest(declaration=declaration):
                status, lines = vr.check_sources(report)
                self.assertNotEqual(status, "FAIL", lines)
                self.assertEqual("official (9/10)" in "\n".join(lines), official)
                result = self.final157_cli(report, "sources")
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertEqual("official (9/10)" in result.stdout, official)


    def test_final164_scalar_properties_cannot_hide_quoted_boundaries(self):
        for properties in ("&label ", "!!str ", "!<tag:yaml.org,2002:str> ", "&label !!str ", "!<tag:yaml.org,2002:str> &label "):
            for container in (False, True):
                value = properties + '"Notes\nfocus: content #"'
                declaration = "title: " + ("{note: " + value + "}" if container else value)
                self.final164_direct_assertions(declaration, self.final143_focus_body(True) + "\nhttps://youtube.com/example [YT]\n")
                # Balanced foreign scalar properties do not declare root focus or depth.
                balanced = properties + '"focus: content # depth: deep"'
                declaration = "title: " + ("{note: " + balanced + "}" if container else balanced)
                report = "---\n" + declaration + "\n---\n" + self.final143_focus_body(True)
                with self.subTest(properties=properties, container=container, balanced=True):
                    metadata = vr.validated_metadata(report)
                    self.assertIsNone(vr.metadata_problem(metadata))
                    self.assertEqual(metadata["focus"], [])
                    self.assertEqual(metadata["depth"], "")
                for check in self.FINAL149_CALLERS:
                    with self.subTest(properties=properties, container=container, balanced=True, check=check):
                        result = self.final157_cli(report, check)
                        self.assertEqual(result.returncode, 0, result.stdout)

    FINAL166_SEQUENCE_QUOTES = (
        'authors:\n  - note: "Notes\nfocus: content #"',
        "authors:\n- note: 'Notes\nfocus: content #'",
        'authors:\n  - "note": "Notes\ndepth: deep #"',
        "authors:\n  - 'note': 'User''s notes\ndepth: deep #'",
        'authors:\n  - - note: "Notes\nfocus: content #"',
        'authors:\n  - note: &name !!str "Notes\nfocus: content #"',
        'authors:\n  - note: !<tag:yaml.org,2002:str> "Notes\ndepth: deep #"',
        '  authors:\n    - note: "Notes\n  focus: content #"',
        'authors:\n  - note: "Notes # not a comment\nfocus: content #"',
        'authors:\n  - note: "Notes \\" escaped\ndepth: deep #"',
    )
    FINAL166_MULTILINE_FLOW = (
        "metadata: {\nfocus: content,\nnote: done}",
        "metadata: {\ndepth: deep,\nnote: done}",
        "metadata: [\n{focus: content},\n{depth: deep}]",
        "metadata: {items: [\nfocus: content,\nnote: done]}",
        "metadata: [{\ndepth: deep,\nnote: done}]",
        "metadata: { # comment 'ignored\nfocus: content,\nnote: done}",
        'metadata: {note: "}",\nfocus: content}',
        "metadata: {note: ']',\ndepth: deep}",
        "metadata:\n  items: {\nfocus: content,\nnote: done}",
        "authors:\n- note: {\nfocus: content,\nnext: done}",
        "authors:\n  - note: &name {\ndepth: deep,\nnext: done}",
        "  metadata: {\n  focus: content,\n  note: done}",
        "metadata: {note: [one, two}\nfocus: content",
        "metadata: [one, two}\ndepth: deep",
    )

    def test_final166_sequence_mapping_quotes_fail_before_all_consumers(self):
        for declaration in self.FINAL166_SEQUENCE_QUOTES:
            self.final164_direct_assertions(declaration, self.final143_focus_body(True) + "\nhttps://youtube.com/example [YT]\n")

    def test_final166_multiline_flow_boundaries_fail_before_all_consumers(self):
        for declaration in self.FINAL166_MULTILINE_FLOW:
            self.final164_direct_assertions(declaration, self.final143_focus_body(True) + "\nhttps://youtube.com/example [YT]\n")

    def final166_assert_valid_report(self, report, expected_focus=(), expected_depth=""):
        metadata = vr.validated_metadata(report)
        self.assertIsNone(vr.metadata_problem(metadata))
        self.assertEqual(metadata["focus"], list(expected_focus))
        self.assertEqual(metadata["depth"], expected_depth)
        self.assertEqual(vr.declared_focus(report), list(expected_focus))
        self.assertEqual(vr.declared_depth(report), expected_depth)
        for checker in (vr.check_focus, vr.check_structure, vr.check_process, vr.check_sources):
            with self.subTest(checker=checker.__name__):
                self.assertNotEqual(checker(report)[0], "FAIL")
        calls = []
        def fetch(*args, **kwargs):
            calls.append(True)
            return 200
        self.assertNotEqual(vr.check_citations(report, fetch=fetch)[0], "FAIL")
        self.assertTrue(calls)
        for check in self.FINAL149_CALLERS:
            with self.subTest(check=check):
                result = self.final157_cli(report, check)
                self.assertEqual(result.returncode, 0, result.stdout)

    def test_final166_plain_foreign_scalars_keep_literal_punctuation(self):
        for title in (
            "Design trends, '90s revival", 'Design trends, "unfinished quotation',
            "Design trends, '90s revival # user's note", "Guides [in progress",
            "Guides {in progress", "It's fine, isn't it", "Design trends, [open notes",
            "Design trends, {open notes", "Design trends:revisited, '90s revival",
        ):
            for prefix in ("title: ", "authors:\n  - note: "):
                with self.subTest(title=title, prefix=prefix):
                    report = "---\n" + prefix + title + "\nfocus: none\ndepth: default\n---\n" + self.final143_focus_body(True)
                    self.final166_assert_valid_report(report, expected_depth="default")

    def test_final166_supported_nested_nodes_do_not_grant_root_authority(self):
        for declaration in (
            'authors:\n  - note: "focus: content # depth: deep"',
            "authors:\n- note: 'User''s focus: content # depth: deep'",
            'authors:\n  - - note: "focus: content"',
            'authors:\n  - note: &name !!str "focus: content"',
            'authors:\n  - note: {"focus":"content", "depth":"deep"}',
            'metadata: {focus: content, values: ["depth: deep", {other: "#"}]}',
            'metadata: [{focus: content}, {depth: deep}]',
            'authors:\n- note: |\n    focus: content\n    depth: deep\n  next: fine',
            'authors:\n  - |\n    focus: content\n    depth: deep',
            'authors:\n  - note: "safe"\n    focus: content\n    depth: deep',
        ):
            with self.subTest(declaration=declaration):
                report = "---\n" + declaration + "\nfocus: none\n---\n" + self.final143_focus_body(True)
                self.final166_assert_valid_report(report)
                only_video = "---\n" + declaration + "\n---\nhttps://youtube.com/example [YT]\n"
                self.assertNotIn("official (9/10)", "\n".join(vr.check_sources(only_video)[1]))
                result = self.final157_cli(only_video, "sources")
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertNotIn("official (9/10)", result.stdout)

    def test_final166_empty_frontmatter_matches_absent_metadata(self):
        body = self.final143_focus_body(True)
        baseline = vr.validated_metadata(body)
        for newline in ("\n", "\r\n"):
            for prefix in ("", "\ufeff", " \n"):
                for inner in ("", newline, "# empty header" + newline):
                    report = prefix + "---" + newline + inner + "---" + newline + body
                    with self.subTest(newline=repr(newline), prefix=repr(prefix), inner=repr(inner)):
                        self.assertEqual(vr.validated_metadata(report), baseline)
                        self.final166_assert_valid_report(report)
                        for checker in (vr.check_focus, vr.check_structure, vr.check_process, vr.check_sources):
                            expected_status, expected_lines = checker(body)
                            # Metadata does not change the verdict. The existing
                            # whole-document word count still includes header tokens.
                            if checker is vr.check_structure:
                                expected_lines = [
                                    "  Word count: " + str(len(report.split()))
                                    if line.startswith("  Word count:") else line
                                    for line in expected_lines
                                ]
                            self.assertEqual(checker(report), (expected_status, expected_lines))

    def final166_assert_rejected_boundary(self, report):
        metadata = vr.validated_metadata(report)
        self.assertIsNotNone(vr.metadata_problem(metadata))
        self.assertEqual(metadata["focus"], [])
        self.assertEqual(metadata["depth"], "")
        self.assertEqual(vr.declared_focus(report), [])
        self.assertEqual(vr.declared_depth(report), "")
        for checker in (vr.check_focus, vr.check_structure, vr.check_process, vr.check_sources):
            status, lines = checker(report)
            self.assertEqual(status, "FAIL", lines)
            self.assertNotIn("official (9/10)", "\n".join(lines))
        calls = []
        def fetch(*args, **kwargs):
            calls.append(True)
            return 200
        self.assertEqual(vr.check_citations(report, fetch=fetch)[0], "FAIL")
        self.assertFalse(calls)

    def test_final166_sequence_prefix_and_key_grammar_direct_matrix(self):
        for spacing in (" ", "   ", " \t "):
            for properties in ("", "&entry ", "!!map ", "&entry !!map "):
                for key in ("note", "'note'", '"note"', "42", "'no''te'", '"n\\"ote"'):
                    for nested in (False, True):
                        prefix = "-" + spacing + ("-" + spacing if nested else "") + properties + key + ": "
                        for quote in ("'", '"'):
                            for field, value in (("focus", "content"), ("depth", "deep")):
                                declaration = "authors:\n  " + prefix + quote + "Notes\n" + field + ": " + value + " #" + quote
                                report = "---\n" + declaration + "\n---\n" + self.final143_focus_body(True) + "\nhttps://youtube.com/example [YT]\n"
                                with self.subTest(spacing=repr(spacing), properties=properties, key=key, nested=nested, quote=quote, field=field):
                                    self.final166_assert_rejected_boundary(report)

    def test_final166_sequence_prefix_representatives_fail_all_cli(self):
        for declaration in (
            'authors:\n  -   note: "Notes\nfocus: content #"',
            "authors:\n- \t note: 'Notes\ndepth: deep #'",
            'authors:\n  - &entry note: "Notes\nfocus: content #"',
            'authors:\n  - !!map "note": "Notes\ndepth: deep #"',
            "authors:\n  -   -   &entry !!map 'note': 'Notes\nfocus: content #'",
            'authors:\n  - 42: "Notes\nfocus: content #"',
            'authors:\n  - &entry - note: "Notes\ndepth: deep #"',
            'authors:\n  - note: {\nfocus: content,\nend: done}',
        ):
            report = "---\n" + declaration + "\n---\n" + self.final143_focus_body(True) + "\nhttps://youtube.com/example [YT]\n"
            for check in self.FINAL149_CALLERS:
                with self.subTest(declaration=declaration, check=check):
                    result = self.final157_cli(report, check)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertNotIn("official (9/10)", result.stdout)
                    self.assertNotIn("not a --deep report", result.stdout)

    def test_final166_balanced_supported_sequence_prefix_controls(self):
        for spacing in (" ", "   ", " \t "):
            for properties in ("", "&entry ", "!!map ", "&entry !!map "):
                for key in ("note", "'note'", '"note"'):
                    for nested in (False, True):
                        declaration = "authors:\n  -" + spacing + ("-" + spacing if nested else "") + properties + key + ': "focus: content # depth: deep"'
                        report = "---\n" + declaration + "\n---\nhttps://youtube.com/example [YT]\n"
                        with self.subTest(declaration=declaration):
                            metadata = vr.validated_metadata(report)
                            self.assertIsNone(vr.metadata_problem(metadata))
                            self.assertEqual(metadata["focus"], [])
                            self.assertEqual(metadata["depth"], "")
                            self.assertNotIn("official (9/10)", "\n".join(vr.check_sources(report)[1]))
        for declaration in (
            'authors:\n  -   note: "safe"',
            'authors:\n  - &entry note: "safe"',
            'authors:\n  -   -   &entry !!map "note": "safe"',
        ):
            with self.subTest(declaration=declaration):
                self.final166_assert_valid_report("---\n" + declaration + "\n---\n" + self.final143_focus_body(True))

    def test_final166_unsupported_mapping_keys_fail_explicitly_even_when_balanced(self):
        for key in ("42", "'no''te'", '"n\\"ote"'):
            declaration = "authors:\n  - " + key + ': "safe"\nfocus: content'
            report = "---\n" + declaration + "\n---\n" + self.final143_focus_body(True) + "\nhttps://youtube.com/example [YT]\n"
            with self.subTest(key=key):
                self.final166_assert_rejected_boundary(report)
            for check in self.FINAL149_CALLERS:
                with self.subTest(key=key, check=check):
                    result = self.final157_cli(report, check)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertNotIn("official (9/10)", result.stdout)

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
