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
    def test_nonstandard_metadata_line_boundaries_cannot_hide_focus(self):
        for separator in ('\x0b', '\x0c', '\x1c', '\x1d', '\x1e', '\x85', '\u2028', '\u2029', '\r'):
            report = '---\ntitle: Report' + separator + 'focus: [security]\n---\nbody'
            with self.subTest(separator=repr(separator)):
                self.assertIsNotNone(vr.root_mapping_problem(report))
                self.assertEqual(vr.declared_focus(report), [])
                self.assertEqual(vr.check_sources(report)[0], 'FAIL')
                if separator != '\r':
                    result = self.cli_focus_result('title: Report' + separator + 'focus: [security]', 'all')
                    self.assertEqual(result.returncode, 1)

    def test_repeated_unclosed_verbatim_tag_prefix_is_bounded(self):
        try:
            result = self.cli_focus_result('focus: ' + '!<,' * 33000 + 'unknown-tag', 'all')
        except subprocess.TimeoutExpired:
            self.fail('repeated malformed tag prefixes stalled validation')
        self.assertEqual(result.returncode, 1)

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

CHECKS = ('focus', 'structure', 'process', 'sources', 'citations', 'all')
BODY = (ROOT / 'tests/fixtures/research-report-good.md').read_text() + '\nhttps://youtube.com/example [YT]\n'
PREFIXES = (
    '? ', 'authors:\n- ? ', 'authors:\n  - ? ', 'authors:\n  -   - ? ',
    'authors:\n  - &entry !!map ? ', 'metadata:\n  ? ', 'metadata:\n  note: ? ',
    'authors: [? ', 'authors: [{? ',
)
DECLARATIONS = tuple(prefix + quote + 'Notes\n' + field + ': ' + value + ' #' + quote
                     for prefix in PREFIXES for quote in ('"', "'")
                     for field, value in (('focus', 'content'), ('depth', 'deep')))

class Final181Test(unittest.TestCase):
    def report(self, declaration):
        return '---\n' + declaration + '\n---\n' + BODY

    def cli(self, report, check):
        if check == 'citations':
            report = vr.URL_RE.sub('offline citation omitted', report)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.md'
            path.write_text(report)
            return subprocess.run([sys.executable, str(ROOT / 'scripts/validate_report.py'), check, str(path), '--offline'],
                                  capture_output=True, text=True, timeout=10,
                                  env={'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1'})

    def test_explicit_key_direct_consumers_reject_before_authority(self):
        for declaration in DECLARATIONS:
            report = self.report(declaration)
            checks = (
                ('root', lambda: vr.root_mapping_problem(report) is not None),
                ('validated', lambda: vr.metadata_problem(vr.validated_metadata(report)) is not None),
                ('focus_identity', lambda: vr.declared_focus(report) == []),
                ('depth_identity', lambda: vr.declared_depth(report) == ''),
            ) + tuple((fn.__name__, lambda fn=fn: fn(report)[0] == 'FAIL')
                      for fn in (vr.check_focus, vr.check_structure, vr.check_process, vr.check_sources))
            for name, check in checks:
                with self.subTest(declaration=declaration, check=name):
                    self.assertTrue(check())

    def test_explicit_key_sources_cannot_grant_official_trust(self):
        report = self.report('authors:\n- ? "Notes\nfocus: content #"')
        status, lines = vr.check_sources(report)
        with self.subTest(check='status'):
            self.assertEqual(status, 'FAIL')
        with self.subTest(check='authority'):
            self.assertNotIn('official (9/10)', '\n'.join(lines))

    def test_explicit_key_citations_fail_before_fetch(self):
        for declaration in DECLARATIONS:
            calls = []
            def fetch(*args, **kwargs):
                calls.append(True)
                return 200
            status = vr.check_citations(self.report(declaration), fetch=fetch)[0]
            with self.subTest(declaration=declaration, check='status'):
                self.assertEqual(status, 'FAIL')
            with self.subTest(declaration=declaration, check='fetch'):
                self.assertFalse(calls)

    def test_explicit_key_all_cli_consumers_reject(self):
        for declaration in (
            'authors:\n- ? "Notes\nfocus: content #"',
            "authors:\n  -   - ? 'Notes\ndepth: deep #'",
            'authors:\n  - &entry !!map ? "Notes\nfocus: content #"',
            'metadata:\n  note: ? "Notes\ndepth: deep #"',
        ):
            for check in CHECKS:
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli(self.report(declaration), check)
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn('official (9/10)', result.stdout)

    def test_literal_question_and_supported_sequence_controls(self):
        for declaration in (
            'title: Why? Continue', 'title: ?word is plain', 'title: "? focus: content"',
            "authors:\n- 'Question? focus: content'", 'authors:\n  - - note: "? focus: content"',
            'authors:\n  - &entry !!map note: "safe"',
            'authors:\n- |\n  ? "Notes\n  focus: content #"',
            'metadata: {note: "? focus: content", values: ["?", safe]}',
        ):
            report = self.report(declaration)
            with self.subTest(declaration=declaration, check='metadata'):
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(report)))
                self.assertEqual(vr.declared_focus(report), [])
                youtube_report = '---\n' + declaration + '\n---\nhttps://youtube.com/example [YT]\n'
                self.assertNotIn('official (9/10)', '\n'.join(vr.check_sources(youtube_report)[1]))
            for check in CHECKS:
                with self.subTest(declaration=declaration, check=check):
                    self.assertEqual(self.cli(report, check).returncode, 0)

    def test_long_nested_sequence_validated_metadata_bounded(self):
        program = (
            'import sys; sys.dont_write_bytecode=True; '
            'sys.path.insert(0, sys.argv[1]); import validate_report as vr; '
            'report="---\\nauthors:\\n  " + "- " * 1000000 + "safe\\n---\\nbody"; '
            'm=vr.validated_metadata(report); '
            'assert vr.metadata_problem(m) is None, m; '
            'assert m["focus"] == [] and m["depth"] == ""; print("PASS")'
        )
        try:
            result = subprocess.run([sys.executable, '-c', program, str(ROOT / 'scripts')],
                                    capture_output=True, text=True, timeout=10,
                                    env={'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1'})
        except subprocess.TimeoutExpired:
            self.fail('1000000 nested sequence prefixes exceeded unchanged 10-second subprocess cap')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'PASS')


FINAL182_PARTIAL = (ROOT / 'tests/fixtures/research-report-good.md').read_text() + '\n## SEO scorecard\nSearch evidence [GSC].\n'
FINAL182_VALUES = ('seo #perf', "'seo' #perf", '"seo" #perf', 'seo\t#perf', 'seo #perf review', 'seo #unknown')
FINAL182_PREFIXES = ('focus: ', 'focus:\n  - ')

class Final182Test(unittest.TestCase):
    def cli(self, declaration, check):
        report = '---\n' + declaration + '\n---\n' + FINAL182_PARTIAL
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.md'
            path.write_text(report)
            return subprocess.run([sys.executable, str(ROOT / 'scripts/validate_report.py'), check, str(path), '--offline'],
                                  capture_output=True, text=True, timeout=10,
                                  env={'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1'})

    def test_plain_tag_then_unspaced_hashtag_fails_direct(self):
        for value in FINAL182_VALUES:
            with self.subTest(value=value, check='scanner'):
                self.assertTrue(vr.scan_focus_value(value)[2])
            for prefix in FINAL182_PREFIXES:
                report = '---\n' + prefix + value + '\n---\n' + FINAL182_PARTIAL
                with self.subTest(value=value, prefix=prefix, check='form'):
                    self.assertIsNotNone(vr.focus_form_problem(report))
                with self.subTest(value=value, prefix=prefix, check='focus'):
                    self.assertEqual(vr.check_focus(report)[0], 'FAIL')
                with self.subTest(value=value, prefix=prefix, check='metadata'):
                    metadata = vr.validated_metadata(report)
                    self.assertIsNotNone(vr.metadata_problem(metadata))
                    self.assertEqual(metadata['focus'], [])

    def test_plain_tag_then_unspaced_hashtag_fails_partial_cli(self):
        for value in FINAL182_VALUES:
            for prefix in FINAL182_PREFIXES:
                for check in ('focus', 'structure', 'all'):
                    with self.subTest(value=value, prefix=prefix, check=check):
                        result = self.cli(prefix + value, check)
                        self.assertEqual(result.returncode, 1)
                        self.assertIn('Focus: FAIL', result.stdout)

    def test_hash_space_comments_remain_comments(self):
        for value in ('seo # performance review', "'seo' # comment with #perf #security", 'seo # #perf #security', 'seo #', 'seo ## heading'):
            for prefix in FINAL182_PREFIXES:
                report = '---\n' + prefix + value + '\n---\n' + FINAL182_PARTIAL
                with self.subTest(value=value, prefix=prefix, check='direct'):
                    self.assertFalse(vr.scan_focus_value(value)[2])
                    self.assertIsNone(vr.focus_form_problem(report))
                    self.assertEqual(vr.declared_focus(report), ['seo'])
                    self.assertEqual(vr.check_focus(report)[0], 'PASS')
                for check in ('focus', 'structure', 'all'):
                    with self.subTest(value=value, prefix=prefix, check=check):
                        self.assertEqual(self.cli(prefix + value, check).returncode, 0)


    def test_nonascii_focus_whitespace_preserves_scalar_identity(self):
        for space in ('\u00a0', '\u2007', '\u202f', '\u3000'):
            for value in ('none' + space + '#security', 'content' + space + '#suffix',
                          'content' + space, space + 'none'):
                for prefix in FINAL182_PREFIXES:
                    report = '---\n' + prefix + value + '\n---\nhttps://youtube.com/example [YT]\n'
                    with self.subTest(space=repr(space), value=value, prefix=prefix, check='identity'):
                        self.assertEqual(vr.declared_focus(report), [value])
                    with self.subTest(space=repr(space), value=value, prefix=prefix, check='focus'):
                        self.assertEqual(vr.check_focus(report)[0], 'FAIL')
                    with self.subTest(space=repr(space), value=value, prefix=prefix, check='source'):
                        status, lines = vr.check_sources(report)
                        self.assertEqual(status, 'FAIL')
                        self.assertNotIn('official (9/10)', '\n'.join(lines))
        for value in ('none\u00a0#security', 'content\u00a0#suffix', 'content\u00a0', '\u00a0none'):
            for prefix in FINAL182_PREFIXES:
                for check in ('focus', 'structure', 'sources', 'all'):
                    with self.subTest(value=value, prefix=prefix, check=check):
                        self.assertEqual(self.cli(prefix + value, check).returncode, 1)

    def test_nonascii_depth_whitespace_is_not_a_comment_separator(self):
        for space in ('\u00a0', '\u2007', '\u202f', '\u3000'):
            for value in ('deep' + space + '#note', 'none' + space + '#security',
                          'deep' + space, space + 'deep'):
                report = '---\ndepth: ' + value + '\n---\n' + FINAL182_PARTIAL
                with self.subTest(space=repr(space), value=value):
                    depth, problem = vr.depth_scalar(report)
                    self.assertEqual(depth, value)
                    self.assertIsNotNone(problem)
                    self.assertEqual(vr.check_process(report)[0], 'FAIL')
        for declaration in ('depth: deep\u00a0#note', 'depth: none\u00a0#security'):
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    # Remove URLs for citations so a broken baseline never reaches the network.
                    report = '---\n' + declaration + '\n---\nno citation URLs'
                    with tempfile.TemporaryDirectory() as tmp:
                        path = Path(tmp) / 'report.md'; path.write_text(report)
                        result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_report.py'), check, str(path), '--offline'],
                                                capture_output=True, text=True, timeout=10,
                                                env={'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1'})
                    self.assertEqual(result.returncode, 1)

    def test_long_whitespace_metadata_parsing_is_bounded(self):
        for form, rejected in (('inline', False), ('continuation', False), ('root', True)):
            program = (
                'import sys; sys.dont_write_bytecode=True; '
                'sys.path.insert(0, sys.argv[1]); import validate_report as vr; '
                'value="a" + " " * 100000 + "b"; '
                'header={"inline":"title: "+value,"continuation":"title:\\n  "+value,"root":value}[sys.argv[2]]; '
                'problem=vr.metadata_problem(vr.validated_metadata("---\\n"+header+"\\n---\\nbody")); '
                'assert (problem is not None) == (sys.argv[2] == "root"), problem; print("PASS")'
            )
            with self.subTest(form=form):
                try:
                    result = subprocess.run([sys.executable, '-c', program, str(ROOT / 'scripts'), form],
                                            capture_output=True, text=True, timeout=10,
                                            env={'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1'})
                except subprocess.TimeoutExpired:
                    self.fail(form + ' 100000-space metadata exceeded unchanged 10-second subprocess cap')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), 'PASS')


FINAL183_SPACES = tuple('\x0b\x0c\x1c\x1d\x1e\x1f\x85\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000')
FINAL183_BODY = (ROOT / 'tests/fixtures/research-report-good.md').read_text() + ''.join(
    '\n## ' + lens['addendum'] + '\nEvidence ' + ''.join('[' + tag + ']' for tag in lens.get('source_tags', [])) + '.\n'
    for lens in vr.MANIFEST['tags'].values())

class Final183Test(unittest.TestCase):
    def report(self, declaration, body=None):
        return '---\n' + declaration + '\n---\n' + (FINAL183_BODY if body is None else body)

    def cli(self, declaration, check):
        report = self.report(declaration)
        if check == 'citations':
            report = vr.URL_RE.sub('offline citation omitted', report)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.md'; path.write_text(report)
            return subprocess.run([sys.executable, str(ROOT / 'scripts/validate_report.py'), check, str(path), '--offline'],
                                  capture_output=True, text=True, timeout=10,
                                  env={'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1'})

    def assert_rejected(self, declaration):
        report = self.report(declaration, 'https://youtube.com/example [YT]\n')
        metadata = vr.validated_metadata(report)
        for name, passed in (
            ('problem', vr.metadata_problem(metadata) is not None),
            ('focus', metadata['focus'] == []),
            ('direct_focus', vr.declared_focus(report) == []),
        ):
            with self.subTest(declaration=repr(declaration), check=name):
                self.assertTrue(passed)
        for fn in (vr.check_focus, vr.check_structure, vr.check_process, vr.check_sources):
            with self.subTest(declaration=repr(declaration), check=fn.__name__):
                status, lines = fn(report)
                self.assertEqual(status, 'FAIL')
                self.assertNotIn('official (9/10)', '\n'.join(lines))
        calls = []
        def fetch(*args, **kwargs):
            calls.append(True)
            return 200
        with self.subTest(declaration=repr(declaration), check='citations'):
            self.assertEqual(vr.check_citations(report, fetch=fetch)[0], 'FAIL')
            self.assertFalse(calls)

    def test_unicode_row_comment_cannot_hide_multiline_node(self):
        for space in FINAL183_SPACES:
            for quote in ('"', "'"):
                for field, value in (('focus', 'content'), ('depth', 'deep')):
                    self.assert_rejected(space + '#note: ' + quote + 'Notes\n' + field + ': ' + value + ' #' + quote)

    def test_unicode_only_rows_are_not_blank_metadata(self):
        for space in FINAL183_SPACES:
            for declaration in (
                space + '\nfocus: content',
                'focus:\n' + space + '\n  - content',
                'depth:\n  ' + space + '\n  deep',
            ):
                self.assert_rejected(declaration)

    def test_focus_sequence_indent_must_remain_consistent(self):
        for first, second in ((0, 2), (2, 4), (4, 2), (2, 0), (0, 4), (4, 0)):
            for a, b in (('content', 'none'), ('none', 'null'), ("'content'", 'none')):
                for middle in ('', '\n  # ordinary comment'):
                    declaration = 'focus:\n' + ' ' * first + '- ' + a + middle + '\n' + ' ' * second + '- ' + b
                    self.assert_rejected(declaration)

    def test_malformed_rows_fail_actual_cli(self):
        declarations = (
            '\u00a0#note: "Notes\nfocus: content #"',
            "\u2007#note: 'Notes\ndepth: deep #'",
            '\u202f\nfocus: content', 'depth:\n  \u3000\n  deep',
            'focus:\n  - content\n    - none', 'focus:\n- none\n  - null',
            'focus:\n    - content\n  - none', 'focus:\n  - content\n- none',
        )
        for declaration in declarations:
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(declaration=repr(declaration), check=check):
                    result = self.cli(declaration, check)
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn('official (9/10)', result.stdout)

    def test_consistent_sequence_indent_and_adjacent_mapping_controls(self):
        for root_indent in (0, 2):
            for item_indent in (0, 2, 4):
                for a, b, expected in (('content', 'none', ['content']), ('none', 'null', [])):
                    declaration = (' ' * root_indent + 'focus: # selected lenses\n' +
                                   ' ' * (root_indent + item_indent) + '- ' + a + '\n' +
                                   ' ' * root_indent + ' # comment with \u00a0#note\n' +
                                   ' ' * (root_indent + item_indent) + '- ' + b + '\n' +
                                   ' ' * root_indent + 'authors:\n' +
                                   ' ' * (root_indent + 2) + '- - safe')
                    report = self.report(declaration)
                    with self.subTest(declaration=repr(declaration), check='direct'):
                        self.assertIsNone(vr.metadata_problem(vr.validated_metadata(report)))
                        self.assertEqual(vr.declared_focus(report), expected)
                        self.assertNotEqual(vr.check_focus(report)[0], 'FAIL')
                        video = self.report(declaration, 'https://youtube.com/example [YT]\n')
                        self.assertEqual('official (9/10)' in '\n'.join(vr.check_sources(video)[1]), bool(expected))
                    for check in ('focus', 'structure', 'all'):
                        with self.subTest(declaration=repr(declaration), check=check):
                            self.assertEqual(self.cli(declaration, check).returncode, 0)

    def test_ascii_comments_quoted_values_and_block_scalar_controls(self):
        for declaration in (
            '# comment\n\t# comment\n \t\nfocus: none',
            'title: "\u00a0#note: focus: content"\nfocus: none',
            "title: '\u2007#note: focus: content'\nfocus: none",
            'title: |\n  \u00a0#note: "Notes\n  focus: content #"\nfocus: none',
            'focus: [content, none]',
            'focus:\n  - content\n  # quoted comment "\n  - none',
        ):
            report = self.report(declaration)
            with self.subTest(declaration=repr(declaration), check='direct'):
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(report)))
                self.assertNotEqual(vr.check_focus(report)[0], 'FAIL')
            for check in ('focus', 'structure', 'all'):
                with self.subTest(declaration=repr(declaration), check=check):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)


FINAL184_BODY = (ROOT / 'tests/fixtures/research-report-good.md').read_text() + ''.join(
    '\n## ' + lens['addendum'] + '\nEvidence ' + ''.join('[' + tag + ']' for tag in lens.get('source_tags', [])) + '.\n'
    for lens in vr.MANIFEST['tags'].values())
FINAL184_SPOOF_PREFIXES = ('metadata:\n  ', 'authors:\n  - ', 'metadata:\n  inner:\n    ', '', 'focus:\n  - ')

class Final184Test(unittest.TestCase):
    def report(self, declaration, body=None):
        return '---\n' + declaration + '\n---\n' + (FINAL184_BODY if body is None else body)

    def cli(self, declaration, check):
        report = self.report(declaration)
        if check == 'citations':
            report = vr.URL_RE.sub('offline citation omitted', report)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.md'
            path.write_text(report)
            return subprocess.run([sys.executable, str(ROOT / 'scripts/validate_report.py'), check, str(path), '--offline'],
                                  capture_output=True, text=True, timeout=10,
                                  env={'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1'})

    def assert_rejected(self, declaration):
        report = self.report(declaration, 'https://youtube.com/example [YT]\n')
        metadata = vr.validated_metadata(report)
        for name, passed in (('root', vr.root_mapping_problem(report) is not None),
                             ('form', vr.focus_form_problem(report) is not None),
                             ('problem', vr.metadata_problem(metadata) is not None),
                             ('focus', metadata['focus'] == []),
                             ('direct_focus', vr.declared_focus(report) == []),
                             ('depth', vr.depth_scalar(report)[1] is not None)):
            with self.subTest(declaration=repr(declaration), check=name):
                self.assertTrue(passed)
        for fn in (vr.check_focus, vr.check_structure, vr.check_process, vr.check_sources):
            with self.subTest(declaration=repr(declaration), check=fn.__name__):
                status, lines = fn(report)
                self.assertEqual(status, 'FAIL')
                self.assertNotIn('official (9/10)', '\n'.join(lines))
        calls = []
        def fetch(*args, **kwargs):
            calls.append(True)
            return 200
        with self.subTest(declaration=repr(declaration), check='citations'):
            self.assertEqual(vr.check_citations(report, fetch=fetch)[0], 'FAIL')
            self.assertFalse(calls)

    def test_colon_key_cannot_hide_multiline_value(self):
        for prefix in FINAL184_SPOOF_PREFIXES:
            for key in ('focus:note', 'depth:note'):
                for quote in ('"', "'"):
                    for target in ('focus: content', 'depth: deep'):
                        self.assert_rejected(prefix + key + ': ' + quote + 'Notes\n' + target + ' #' + quote)

    def test_unsupported_colon_key_does_not_become_focus(self):
        for prefix in FINAL184_SPOOF_PREFIXES:
            for ending in (' content', '', '\n  content'):
                self.assert_rejected(prefix + 'focus:note:' + ending)

    def test_colon_key_spoof_fails_all_cli_consumers(self):
        declarations = (
            'metadata:\n  focus:note: "Notes\nfocus: content #"',
            "authors:\n  - focus:note: 'Notes\ndepth: deep #'",
            'metadata:\n  inner:\n    focus:note: "Notes\nfocus: content #"',
            'focus:note: "Notes\nfocus: content #"',
            'focus:\n  - focus:note: "Notes\nfocus: content #"',
            'focus:\n  - depth:note: "Notes\nfocus: content #"',
        )
        for declaration in declarations:
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli(declaration, check)
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn('official (9/10)', result.stdout)

    def test_exact_keys_and_literal_colon_controls(self):
        cases = (
            ('focus: content', ['content']),
            ("'focus': 'content'", ['content']),
            ('"focus" : [content]', ['content']),
            ('focus:\tcontent', ['content']),
            ('focus:\n  - content\n  - # ordinary comment\n  -', ['content']),
            ('metadata:\n  focus: content\n  depth: deep', []),
            ('metadata:\n  "focus:note": "Notes"', []),
            ("authors:\n  - 'focus:note': 'Notes'", []),
            ('title: "focus:note: content"', []),
            ('title: focus:note\nfocus: none', []),
            ('metadata:\n  focus-note: "Notes"', []),
        )
        for declaration, expected in cases:
            report = self.report(declaration)
            with self.subTest(declaration=declaration, check='direct'):
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(report)))
                self.assertEqual(vr.declared_focus(report), expected)
                self.assertEqual(vr.check_focus(report)[0], 'PASS')
                video = self.report(declaration, 'https://youtube.com/example [YT]\n')
                self.assertEqual('official (9/10)' in '\n'.join(vr.check_sources(video)[1]), bool(expected))
            for check in ('focus', 'structure', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)

    def test_block_focus_internal_whitespace_is_bounded(self):
        declaration = 'focus:\n  - x' + ' ' * 100000 + 'y'
        for check in ('focus', 'all'):
            with self.subTest(check=check):
                try:
                    result = self.cli(declaration, check)
                except subprocess.TimeoutExpired:
                    self.fail(check + ' 100000-space block item exceeded unchanged 10-second subprocess cap')
                self.assertEqual(result.returncode, 1)

    def test_long_block_focus_valid_controls_are_bounded(self):
        for declaration in ('focus:\n  - seo', 'focus:\n  - seo' + ' ' * 100000,
                            'focus:\n  - ' + ' ' * 100000 + 'seo'):
            with self.subTest(form='ordinary' if len(declaration) < 100 else ('trailing' if declaration.endswith(' ') else 'leading')):
                result = self.cli(declaration, 'all')
                self.assertEqual(result.returncode, 0)


class Final185Test(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli

    def test_reserved_hashtag_with_plain_suffix_is_rejected(self):
        for tag in set(MANIFEST['tags']) | set(MANIFEST.get('bundles', {})):
            for separator in (' ', '\t'):
                for suffix in ('devtools', 'review', '#comment'):
                    declaration = 'focus: #' + tag + separator + suffix
                    with self.subTest(declaration=declaration):
                        self.assertEqual(vr.check_focus(self.report(declaration))[0], 'FAIL')
                        self.assertEqual(self.cli(declaration, 'all').returncode, 1)

    def test_ordinary_comment_and_explicit_focus_controls(self):
        for declaration in ("focus: #selected user's lenses", 'focus: # selected lenses'):
            self.assertEqual(vr.check_focus(self.report(declaration))[0], 'PASS')
            self.assertEqual(self.cli(declaration, 'all').returncode, 0)
        for declaration in ('focus: #security', 'focus: [security, devtools]', 'focus: security, devtools'):
            self.assertEqual(vr.check_focus(self.report(declaration, 'body'))[0], 'FAIL')
            self.assertEqual(self.cli(declaration, 'all').returncode, 0)

    def test_nested_plain_focus_is_not_root_csv(self):
        for declaration in ("metadata:\n  focus: Design trends, '90s revival",
                            "authors:\n  - focus: Design trends, '90s revival",
                            "metadata:\n  inner:\n    focus: Design trends, '90s revival"):
            with self.subTest(declaration=declaration):
                self.assertIsNone(vr.root_mapping_problem(self.report(declaration)))
                self.assertEqual(self.cli(declaration, 'all').returncode, 0)
        self.assertEqual(self.cli("focus: security, 'devtools", 'all').returncode, 1)

    def test_unpaired_surrogate_is_printable_failure(self):
        declaration = r'focus: "\ud800"'
        for check in ('focus', 'all'):
            result = self.cli(declaration, check)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn('Traceback', result.stderr)
            self.assertIn('unknown focus tag', result.stdout)


class Final186Test(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli

    def test_known_hashtag_before_block_list_is_ambiguous(self):
        for tag in set(MANIFEST['tags']) | set(MANIFEST.get('bundles', {})):
            for header in ('#' + tag, '#selected #' + tag, '# selected #' + tag):
                declaration = 'focus: ' + header + '\n  - security'
                with self.subTest(header=header):
                    self.assertIsNotNone(vr.focus_form_problem(self.report(declaration)))
                    self.assertEqual(self.cli(declaration, 'all').returncode, 1)

    def test_unknown_comment_block_controls_remain_valid(self):
        for header in ('#none', '#selected', '# selected lenses', "#selected user's lenses"):
            declaration = 'focus: ' + header + '\n  - security'
            self.assertIsNone(vr.focus_form_problem(self.report(declaration)))
            self.assertEqual(self.cli(declaration, 'all').returncode, 0)

    def test_indentless_sequence_after_scalar_is_rejected(self):
        for declaration in ('title: Report\n- focus: [security]', 'metadata: text\n- note'):
            self.assertIsNotNone(vr.root_mapping_problem(self.report(declaration)))
            self.assertEqual(self.cli(declaration, 'all').returncode, 1)
        for declaration in ('metadata:\n- note', 'metadata: # notes\n- note', 'focus:\n- security'):
            self.assertIsNone(vr.root_mapping_problem(self.report(declaration)))
            self.assertEqual(self.cli(declaration, 'all').returncode, 0)


class Final187Test(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli

    def test_many_distinct_unknown_tags_are_bounded(self):
        declaration = 'focus: [' + ','.join('unknown-tag-' + str(i) for i in range(100000)) + ']'
        for check in ('process', 'citations'):
            with self.subTest(check=check):
                try:
                    result = self.cli(declaration, check)
                except subprocess.TimeoutExpired:
                    self.fail(check + ' distinct tags exceeded unchanged 10-second cap')
                self.assertEqual(result.returncode, 1)
                self.assertIn('unknown focus tag', result.stdout)

    def test_expansion_keeps_order_and_duplicates_controls(self):
        tags = ['security', 'unknown-one', 'security', 'unknown-two', 'unknown-one']
        self.assertEqual(vr.expand_focus(tags), ['security', 'unknown-one', 'unknown-two'])
        self.assertEqual(vr.expand_focus(['launch', 'launch']), vr.expand_focus(['launch']))
        self.assertEqual(self.cli('focus: [security, security]', 'all').returncode, 0)




class Final188ParentBoundary(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    INLINE_VALUES = ('Report', '"Report"', "'Report'", '[Report]', '{name: Report}', '&title !!str "Report"')
    BAD_ROWS = ('focus: [security]', 'depth: deep', '- focus: [security]', 'continued report')
    BAD_NESTED = (
        'metadata:\n  title: Report\n    focus: content',
        'metadata:\n  inner:\n    title: Report\n      depth: deep',
        'authors:\n  - title: Report\n      focus: content',
        'authors:\n  - Report\n    depth: deep',
        'authors:\n  - - title: Report\n        focus: content',
        '  title: Report\n    focus: [security]\n    depth: deep',
        'title: Report\n  # ignored comment\n\n  depth: deep',
    )
    CONTROLS = (
        'title: Report\nfocus: none\ndepth: default',
        'metadata:\n  focus: [security]\n  depth: deep',
        'metadata:\n  title: Report\n  focus: content\n  depth: deep',
        'metadata:\n  inner:\n    title: Report\n    depth: deep',
        'authors:\n  - title: Report\n    focus: content\n    depth: deep',
        'authors:\n- title: Report\n  focus: content',
        'authors:\n  - - title: Report\n      focus: content',
        'authors:\n  - title:\n      focus: content\n    depth: deep',
        'title: |\n  focus: content\n  depth: deep',
        'metadata:\n  title: >-\n    focus: content\n  depth: deep',
        'authors:\n  - |\n    focus: content\n    depth: deep',
        'title:\n  Report\nfocus: none',
        'metadata: # empty parent\n  focus: content',
    )

    def assert_invalid_parent(self, declaration):
        report = self.report(declaration, 'https://youtube.com/example [YT]\n')
        metadata = vr.validated_metadata(report)
        conditions = (
            ('root', vr.root_mapping_problem(report) is not None),
            ('form', vr.focus_form_problem(report) is not None),
            ('validated', vr.metadata_problem(metadata) is not None),
            ('no_focus', metadata['focus'] == [] and vr.declared_focus(report) == []),
            ('no_depth', metadata['depth'] == '' and vr.depth_scalar(report)[1] is not None),
        )
        for name, passed in conditions:
            with self.subTest(declaration=declaration, check=name):
                self.assertTrue(passed)
        for check in (vr.check_focus, vr.check_structure, vr.check_process, vr.check_sources):
            with self.subTest(declaration=declaration, check=check.__name__):
                status, lines = check(report)
                self.assertEqual(status, 'FAIL')
                self.assertNotIn('official (9/10)', '\n'.join(lines))
        calls = []
        def fetch(*args, **kwargs):
            calls.append(True)
            return 200
        with self.subTest(declaration=declaration, check='citations_before_fetch'):
            self.assertEqual(vr.check_citations(report, fetch=fetch)[0], 'FAIL')
            self.assertFalse(calls)

    def test_indented_rows_cannot_extend_completed_root_values(self):
        for value in self.INLINE_VALUES:
            for row in self.BAD_ROWS:
                self.assert_invalid_parent('title: ' + value + '\n  ' + row)

    def test_nested_completed_values_cannot_become_parents(self):
        for declaration in self.BAD_NESTED:
            self.assert_invalid_parent(declaration)

    def test_malformed_parent_rejected_by_all_cli_consumers(self):
        declarations = ('title: Report\n  focus: [security]\n  depth: deep',
                        'title: "Report"\n  depth: deep',
                        'metadata:\n  title: Report\n    focus: content',
                        'authors:\n  - title: Report\n      depth: deep')
        for declaration in declarations:
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli(declaration, check)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn('inline metadata value', result.stdout)
                    self.assertNotIn('official (9/10)', result.stdout)

    def test_valid_nested_mappings_and_block_scalars_keep_no_root_authority(self):
        for declaration in self.CONTROLS:
            report = self.report(declaration)
            with self.subTest(declaration=declaration, check='metadata'):
                metadata = vr.validated_metadata(report)
                self.assertIsNone(vr.metadata_problem(metadata))
                self.assertEqual(metadata['focus'], [])
                self.assertEqual(metadata['depth'], 'default' if 'depth: default' in declaration else '')
                video = self.report(declaration, 'https://youtube.com/example [YT]\n')
                self.assertNotIn('official (9/10)', '\n'.join(vr.check_sources(video)[1]))
            for check in ('focus', 'structure', 'process', 'sources', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)


class Final189InlineSequence(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    PREFIXES = ('title: - ', 'title:\t-\t', 'title: &note !!str - ',
                'metadata:\n  note: - ', 'authors:\n  - note: - ',
                'metadata: {note: - ')

    def test_inline_sequence_indicator_cannot_conceal_quoted_root_metadata(self):
        for prefix in self.PREFIXES:
            for quote in ('"', "'"):
                for target in ('focus: content', 'depth: deep'):
                    self.assert_invalid_parent(prefix + quote + 'Notes\n' + target + ' #' + quote)
        for declaration in ('title: - [content]', 'title: - item', 'metadata: {note: - item}'):
            self.assert_invalid_parent(declaration)

    def test_inline_sequence_indicator_fails_all_cli_consumers(self):
        for declaration in ('title: - "Notes\nfocus: content #"',
                            "title: - 'Notes\ndepth: deep #'",
                            'metadata:\n  note: - "Notes\nfocus: content #"',
                            "authors:\n  - note: - 'Notes\nfocus: content #'",
                            'title: &note !!str - "Notes\nfocus: content #"'):
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli(declaration, check)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn('sequence indicator', result.stdout)
                    self.assertNotIn('official (9/10)', result.stdout)

    def test_row_sequences_sentinels_and_literal_dash_controls_remain_valid(self):
        for declaration in ('focus: -', 'focus: - # ordinary comment', 'depth: -',
                            'title: -word', 'title: "- content"', "title: '- content'",
                            'title: Report - "unfinished quote',
                            'authors:\n  - "focus: content"',
                            'authors:\n- - "focus: content"',
                            'authors:\n  - note: "- content"\n    depth: deep',
                            'title: |\n  - "Notes\n  focus: content #"'):
            with self.subTest(declaration=declaration):
                metadata = vr.validated_metadata(self.report(declaration))
                self.assertIsNone(vr.metadata_problem(metadata))
                self.assertEqual(metadata['focus'], [])
                for check in ('focus', 'structure', 'process', 'sources', 'all'):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)

    def test_parent_presence_depends_on_value_prefix_not_comment_contents(self):
        for parent in ('', '# comment ["', '&parent # comment ["', '!<tag:yaml.org,2002:map> # comment ["'):
            declaration = 'metadata: ' + parent + '\n  focus: content\n  depth: deep'
            with self.subTest(parent=parent):
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration))))
                self.assertEqual(self.cli(declaration, 'all').returncode, 0)
        for parent in ('"# comment"', "'# comment'", '[content]', '{name: content}', '&name "# comment"'):
            self.assert_invalid_parent('metadata: ' + parent + '\n  focus: content')


class Final189SentinelSpacing(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli

    def test_no_focus_sentinel_retains_csv_and_flow_spacing(self):
        for declaration in ('focus: -, security', 'focus: - , security',
                            'focus: [ - , security ]', 'focus: security, - ',
                            'focus: [security, - ]'):
            with self.subTest(declaration=declaration):
                self.assertEqual(vr.declared_focus(self.report(declaration)), ['security'])
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration))))
                self.assertEqual(self.cli(declaration, 'all').returncode, 0)


class Final190MetadataBoundaries(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    BAD_BLOCKS = (
        'title: |\n  text\n "unterminated\nfocus: content',
        "title: >-\n   text\n  'unterminated\ndepth: deep",
        'title: |2\n text\nfocus: content',
        'title: >2-\n  text\n focus: content\nfocus: content',
        'title: |-2\n  text\n depth: deep\nfocus: content',
        'metadata:\n  title: |\n    text\n   "unterminated\nfocus: content',
        'authors:\n  - title: |\n      text\n     "unterminated\nfocus: content',
        'authors:\n  - |\n    text\n   "unterminated\nfocus: content',
        'authors:\n  - title: |2\n     text\nfocus: content',
        'title: &note !!str |2\n text\nfocus: content',
        'title: |\n  # scalar content establishes indent\n "unterminated\nfocus: content',
    )
    BLOCK_CONTROLS = (
        'title: |\n  focus: content\n  depth: deep',
        'title: >-\n  text\n    focus: content\n  depth: deep',
        'title: |2\n  focus: content\n  depth: deep',
        'title: >2-\n  text\n\n  focus: content',
        'title: |-2\n  text\n # exterior comment\nfocus: none',
        'title: |\n  text\n # exterior comment\nfocus: none',
        'title: |\n\n  # scalar content\n  focus: content',
        'metadata:\n  title: |2\n    focus: content\n  owner: local',
        'authors:\n  - title: |2\n      focus: content\n    owner: local',
        'authors:\n  - |2\n    focus: content\n    depth: deep',
        'title: &note !!str |2\n  focus: content',
        'title: |2\nfocus: none',
    )
    PROPERTY_CONTROLS = tuple(
        declaration
        for prop in ('&parent', '!!map', '!<tag:yaml.org,2002:map>', '&parent !!map', '!!map &parent')
        for declaration in (
            'metadata: ' + prop + '\n  focus: content\n  depth: deep',
            'metadata: ' + prop + ' \n  focus: content',
            'metadata: ' + prop + ' # parent\n  focus: content',
            'metadata:\n  inner: ' + prop + '\n    focus: content',
            'authors:\n  - ' + prop + '\n    focus: content',
            'authors:\n  - note: ' + prop + '\n      focus: content\n    owner: local',
        )
    )

    def test_block_scalar_partial_dedent_cannot_grant_metadata_authority(self):
        for declaration in self.BAD_BLOCKS:
            self.assert_invalid_parent(declaration)

    def test_invalid_scalar_indentation_fails_all_cli_consumers(self):
        for declaration in self.BAD_BLOCKS[:5] + self.BAD_BLOCKS[6:9]:
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli(declaration, check)
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn('official (9/10)', result.stdout)

    def test_valid_block_scalar_boundaries_remain_inert(self):
        for declaration in self.BLOCK_CONTROLS:
            with self.subTest(declaration=declaration):
                report = self.report(declaration)
                metadata = vr.validated_metadata(report)
                self.assertIsNone(vr.metadata_problem(metadata))
                self.assertEqual(metadata['focus'], [])
                self.assertEqual(metadata['depth'], '')
                video = self.report(declaration, 'https://youtube.com/example [YT]\n')
                self.assertNotIn('official (9/10)', '\n'.join(vr.check_sources(video)[1]))
                for check in ('focus', 'structure', 'process', 'sources', 'all'):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)

    def test_property_only_parents_with_and_without_trailing_space_are_equivalent(self):
        for declaration in self.PROPERTY_CONTROLS:
            with self.subTest(declaration=declaration):
                metadata = vr.validated_metadata(self.report(declaration))
                self.assertIsNone(vr.metadata_problem(metadata))
                self.assertEqual(metadata['focus'], [])
                self.assertEqual(metadata['depth'], '')
                video = self.report(declaration, 'https://youtube.com/example [YT]\n')
                self.assertNotIn('official (9/10)', '\n'.join(vr.check_sources(video)[1]))
                for check in ('focus', 'structure', 'process', 'sources', 'all'):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)

    def test_properties_do_not_make_completed_values_into_parents(self):
        for prop in ('&parent', '!!map', '!<tag:yaml.org,2002:map>', '&parent !!map'):
            for value in ('"Report"', '[Report]', '{name: Report}'):
                self.assert_invalid_parent('metadata: ' + prop + ' ' + value + '\n  focus: content')

    def test_many_spaced_dash_sentinels_remain_bounded(self):
        declaration = 'focus: [' + '- , ' * 250000 + 'security]'
        for check in ('process', 'all'):
            with self.subTest(check=check):
                try:
                    result = self.cli(declaration, check)
                except subprocess.TimeoutExpired:
                    self.fail(check + ' spaced sentinels exceeded unchanged 10-second subprocess cap')
                self.assertEqual(result.returncode, 0)


class Final191MetadataParents(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    INVALID_DEDENTS = (
        'metadata:\n  child: value\n orphan: value\nfocus: content',
        'metadata:\n    child: value\n  orphan: value\nfocus: content',
        'metadata:\n  child:\n    leaf: value\n   orphan: value\nfocus: content',
        'metadata:\n  child:\n    leaf: value\n orphan: value\ndepth: deep',
        'authors:\n  - name: local\n   orphan: value\nfocus: content',
        'authors:\n  - title:\n      child: value\n     orphan: value\nfocus: content',
        'authors:\n- title:\n    child: value\n   orphan: value\nfocus: content',
        'authors:\n  - - title: value\n     orphan: value\nfocus: content',
        'metadata: &parent\n  child: value\n # exterior comment\n orphan: value\nfocus: content',
    )
    VALID_DEDENTS = (
        'metadata:\n  child: value\n  sibling: value\nfocus: none',
        'metadata:\n    child: value\n    sibling: value\nfocus: none',
        'metadata:\n  child:\n    leaf: value\n  sibling: value\nfocus: none',
        'authors:\n  - name: local\n    sibling: value\n  - name: other',
        'authors:\n  - title:\n      child: value\n    sibling: value\nfocus: none',
        'authors:\n- title:\n    child: value\n  sibling: value\nfocus: none',
        'authors:\n  - - title: value\n      sibling: value\n    - title: other',
        'metadata: &parent\n  child: value\n # exterior comment\n  sibling: value\nfocus: none',
        'title:\n  Plain text\nfocus: none',
        'depth:\n  default\nfocus: none',
    )
    STANDALONE_SCALARS = tuple(
        declaration
        for indicator in ('|', '|2', '>-', '>2-', '|-2')
        for declaration in (
            'title:\n  ' + indicator + '\n  "unfinished\nfocus: none',
            'title: &note\n  ' + indicator + '\n  [unfinished\nfocus: none',
            'metadata:\n  title:\n    ' + indicator + '\n    "unfinished\n  owner: local',
            'authors:\n  - title:\n      ' + indicator + '\n      [unfinished\n    owner: local',
            'authors:\n  -\n    ' + indicator + '\n    "unfinished\nfocus: none',
        )
    )

    def test_unopened_mapping_dedents_cannot_grant_authority(self):
        for declaration in self.INVALID_DEDENTS:
            self.assert_invalid_parent(declaration)

    def test_unopened_mapping_dedents_fail_all_cli_consumers(self):
        for declaration in self.INVALID_DEDENTS:
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli(declaration, check)
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn('official (9/10)', result.stdout)

    def test_established_mapping_and_sequence_dedents_remain_valid(self):
        for declaration in self.VALID_DEDENTS:
            with self.subTest(declaration=declaration):
                metadata = vr.validated_metadata(self.report(declaration))
                self.assertIsNone(vr.metadata_problem(metadata))
                self.assertEqual(metadata['focus'], [])
                for check in ('focus', 'structure', 'all'):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)

    def test_standalone_block_indicator_uses_its_empty_parent_indent(self):
        for declaration in self.STANDALONE_SCALARS:
            with self.subTest(declaration=declaration):
                report = self.report(declaration)
                metadata = vr.validated_metadata(report)
                self.assertIsNone(vr.metadata_problem(metadata))
                self.assertEqual(metadata['focus'], [])
                self.assertEqual(metadata['depth'], '')
                video = self.report(declaration, 'https://youtube.com/example [YT]\n')
                self.assertNotIn('official (9/10)', '\n'.join(vr.check_sources(video)[1]))
                for check in ('focus', 'structure', 'process', 'sources', 'all'):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)
        for declaration in ('title:\n  |2\n "partial\nfocus: content',
                            'metadata:\n  title:\n    |2\n   [partial\nfocus: content'):
            self.assert_invalid_parent(declaration)

    def test_each_cli_invocation_validates_metadata_once(self):
        from unittest.mock import patch
        for declaration, expected in (('focus: [security]', 0),
                                      ('title: "unterminated\nfocus: content', 1)):
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                report = self.report(declaration)
                with self.subTest(declaration=declaration, check=check), tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / 'report.md'; path.write_text(report)
                    with patch.object(vr, 'validated_metadata', wraps=vr.validated_metadata) as parse, \
                            patch.object(vr, 'classify_citation', return_value=('live', '')):
                        with redirect_stdout(io.StringIO()):
                            result = vr.main([check, str(path), '--offline'])
                    self.assertEqual(result, expected)
                    self.assertEqual(parse.call_count, 1)

    def test_direct_consumers_revalidate_each_report_without_stale_state(self):
        from unittest.mock import patch
        bad = self.report('title: "unterminated\nfocus: content', 'https://youtube.com/example [YT]\n')
        good = self.report('focus: none')
        for check in (vr.check_focus, vr.check_structure, vr.check_process, vr.check_sources):
            with self.subTest(check=check.__name__), patch.object(vr, 'validated_metadata', wraps=vr.validated_metadata) as parse:
                self.assertNotEqual(check(good)[0], 'FAIL')
                self.assertEqual(check(bad)[0], 'FAIL')
                self.assertNotEqual(check(good)[0], 'FAIL')
                self.assertEqual(parse.call_count, 3)
        calls = []
        with patch.object(vr, 'validated_metadata', wraps=vr.validated_metadata) as parse:
            self.assertEqual(vr.check_citations(bad, fetch=lambda *args: calls.append(True))[0], 'FAIL')
            self.assertFalse(calls)
            self.assertEqual(parse.call_count, 1)




class Final192PendingParents(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    INVALID_SEQUENCES = (
        'metadata:\n  note: safe\n  - extra\nfocus: content',
        'metadata:\n  note: "safe"\n  - extra\nfocus: content',
        'metadata:\n  note: [safe]\n  - extra\ndepth: deep',
        'metadata:\n  note: {name: safe}\n  - extra\nfocus: content',
        'metadata:\n  inner:\n    note: safe\n    - extra\nfocus: content',
        'authors:\n  - note: safe\n    - extra\nfocus: content',
        'authors:\n- note: safe\n  - extra\nfocus: content',
        'authors:\n  - - note: safe\n      - extra\nfocus: content',
        'metadata:\n  note:\n  - first\n  owner: safe\n  - extra\nfocus: content',
        'metadata:\n  note: safe\n  # comment\n\n  - extra\nfocus: content',
        'metadata:\n  note: &value "safe"\n  - extra\nfocus: content',
        'metadata:\n  note: |\n    safe\n  - extra\nfocus: content',
    )
    INVALID_BLOCKS = (
        'metadata:\n  a: x\n  |\n    "Notes\nfocus: content',
        'metadata:\n  a: x\n  |2\n    "Notes\nfocus: content',
        'metadata:\n  a: x\n  >-\n    [Notes\nfocus: content',
        'metadata:\n  a: [x]\n  |\n    "Notes\nfocus: content',
        'metadata:\n  a: x\n  &note\n  |\n    "Notes\nfocus: content',
        'authors:\n  - a: x\n    |\n      "Notes\nfocus: content',
        'authors:\n  - a: x\n    &note\n    >-\n      [Notes\nfocus: content',
        'metadata:\n  a: x\n  # comment\n  |\n    "Notes\nfocus: content',
        'metadata:\n  a:\n  |\n    "Notes\nfocus: content',
        'metadata:\n  items:\n  - one\n  |\n    "Notes\nfocus: content',
    )
    PROPERTY_BLOCKS = tuple(
        declaration
        for prop in ('&note', '!!str', '!<tag:yaml.org,2002:str>', '&note !!str')
        for indicator in ('|', '|2', '>2-')
        for declaration in (
            'title:\n  ' + prop + '\n  ' + indicator + '\n  "unfinished\nfocus: none',
            'metadata:\n  title:\n    ' + prop + '\n    ' + indicator + '\n    [unfinished\n  owner: local',
            'authors:\n  - title:\n      ' + prop + '\n      ' + indicator + '\n      "unfinished\n    owner: local',
            'authors:\n  -\n    ' + prop + '\n    ' + indicator + '\n    [unfinished\nfocus: none',
        )
    ) + (
        'title:\n  &note\n  !!str\n  |2\n  "unfinished\nfocus: none',
        'title:\n  &note # property\n  # comment\n  !!str\n  |2\n  [unfinished\nfocus: none',
        'metadata:\n  title:\n    &note\n    !!str\n    |2\n    "unfinished\n  owner: local',
    )
    CONTAINER_CONTROLS = (
        'metadata:\n  notes:\n  - first\n  - second\n  owner: local',
        'metadata:\n  notes: # empty\n  - first\n  owner: local',
        'metadata:\n  notes: &items\n  - first\n  owner: local',
        'metadata:\n  notes:\n    - first\n    - second\n  owner: local',
        'authors:\n  - notes:\n    - first\n    - second\n    owner: local',
        'authors:\n- notes:\n  - first\n  owner: local',
        'authors:\n  - - notes:\n      - first\n      owner: local',
        'authors:\n  - first\n  - second',
        'authors:\n  - - first\n    - second\n  - third',
        'authors:\n  - &item\n    owner: local\n    notes:\n    - one',
        'metadata:\n  &parent\n  owner: local',
        'title:\n  &note\n  "ordinary text"\nfocus: none',
        'title: "|"\nfocus: none',
        'focus:\n- security\n- content',
    )

    def test_nested_sequences_need_an_empty_mapping_parent(self):
        for declaration in self.INVALID_SEQUENCES:
            self.assert_invalid_parent(declaration)

    def test_invalid_nested_sequences_fail_all_cli_consumers(self):
        for declaration in self.INVALID_SEQUENCES:
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    self.assertEqual(self.cli(declaration, check).returncode, 1)

    def test_standalone_properties_preserve_the_block_parent(self):
        for declaration in self.PROPERTY_BLOCKS:
            with self.subTest(declaration=declaration):
                metadata = vr.validated_metadata(self.report(declaration))
                self.assertIsNone(vr.metadata_problem(metadata))
                self.assertEqual(metadata['focus'], [])
                self.assertEqual(metadata['depth'], '')
                video = self.report(declaration, 'https://youtube.com/example [YT]\n')
                self.assertNotIn('official (9/10)', '\n'.join(vr.check_sources(video)[1]))
                for check in (vr.check_focus, vr.check_structure, vr.check_process):
                    self.assertNotEqual(check(self.report(declaration))[0], 'FAIL')
                self.assertEqual(vr.check_citations(video, fetch=lambda *args: 200)[0], 'PASS')

    def test_property_block_controls_pass_cli_consumers(self):
        for declaration in self.PROPERTY_BLOCKS[::8] + self.PROPERTY_BLOCKS[-3:]:
            for check in ('focus', 'structure', 'process', 'sources', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)

    def test_standalone_block_indicator_requires_a_pending_empty_parent(self):
        for declaration in self.INVALID_BLOCKS:
            self.assert_invalid_parent(declaration)

    def test_unparented_block_indicators_fail_all_cli_consumers(self):
        for declaration in self.INVALID_BLOCKS:
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    self.assertEqual(self.cli(declaration, check).returncode, 1)

    def test_valid_nested_containers_and_property_scalars_remain_supported(self):
        for declaration in self.CONTAINER_CONTROLS:
            with self.subTest(declaration=declaration):
                metadata = vr.validated_metadata(self.report(declaration))
                self.assertIsNone(vr.metadata_problem(metadata))
                self.assertEqual(metadata['focus'], ['security', 'content'] if declaration.startswith('focus:') else [])
                for check in ('focus', 'structure', 'process', 'sources', 'all'):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)

    def test_standalone_properties_preserve_explicit_four_indent(self):
        for declaration in (
            'title:\n  &note\n  |4\n    text\nfocus: none',
            'title:\n  !!str\n  |4\n    "unfinished\nfocus: none',
            'metadata:\n  title:\n    &note\n    >4-\n      [unfinished\n  owner: local',
            'authors:\n  -\n    &note\n    |4\n      "unfinished\nfocus: none',
        ):
            with self.subTest(declaration=declaration):
                metadata = vr.validated_metadata(self.report(declaration))
                self.assertIsNone(vr.metadata_problem(metadata))
                self.assertEqual(metadata['focus'], [])
                for check in ('focus', 'structure', 'process', 'sources', 'all'):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)



    def test_completed_nested_containers_consume_empty_parent(self):
        for declaration in (
            'metadata:\n  note: safe\n- extra\nfocus: content',
            'metadata:\n  notes:\n    owner: local\n  - extra\nfocus: content',
            'metadata:\n  notes:\n    - first\n  - extra\nfocus: content',
            'metadata:\n  notes:\n    &item\n    owner: local\n  - extra\nfocus: content',
            'metadata:\n  notes:\n    "safe"\n  - extra\nfocus: content',
            'metadata:\n  notes:\n    |2\n    safe\n  - extra\nfocus: content',
        ):
            self.assert_invalid_parent(declaration)
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    self.assertEqual(self.cli(declaration, check).returncode, 1)




class Final193StandaloneNodes(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    VALUES = ('"safe"', "'safe'", '[safe]', '{name: safe}', '&note "safe"',
              '!!str "safe"', '""', '[]', '{}')
    INVALID_ORPHANS = tuple(
        template.replace('VALUE', value)
        for value in VALUES + ('plain text',)
        for template in (
            'metadata:\n  name: safe\n  VALUE\nfocus: content',
            'authors:\n  - name: safe\n    VALUE\nfocus: content',
            'metadata:\n  items:\n  - first\n  VALUE\nfocus: content',
        )
    )
    COMPLETED_SCALARS = tuple(
        template.replace('VALUE', value).replace('CHILD', child)
        for value in VALUES
        for child in ('child: value', '- extra', '"orphan"', '{child: value}')
        for template in (
            'metadata:\n  VALUE\n  CHILD\nfocus: content',
            'metadata:\n  title:\n    VALUE\n    CHILD\nfocus: content',
            'authors:\n  -\n    VALUE\n    CHILD\nfocus: content',
        )
    )
    PROPERTY_CONTROLS = tuple(
        'title:\n' + ' ' * prop_indent + prop + '\n' + ' ' * node_indent + node + '\nfocus: none'
        for prop_indent, node_indent in ((4, 2), (2, 4), (6, 2), (6, 4), (2, 6))
        for prop in ('&note', '!!str')
        for node in ('"safe"', '|2\n  "unfinished', '>4-\n    [unfinished')
    ) + (
        'metadata:\n      &parent\n  name: local\nfocus: none',
        'metadata:\n  &parent\n      name: local\nfocus: none',
        'metadata:\n  title:\n      &note\n    |2\n    "unfinished\n  owner: local',
        'metadata:\n  title:\n    &note\n      [safe]\n  owner: local',
        'authors:\n  -\n      &note\n    |2\n    "unfinished\n  - other',
        'authors:\n  - title:\n        &note\n      "safe"\n    owner: local',
        'title:\n      &note\n  # comment\n    !!str\n  |2\n  "unfinished\nfocus: none',
        'items:\n    &items\n  - first\n  - second\nfocus: none',
    )
    SCALAR_CONTROLS = tuple(
        template.replace('VALUE', value)
        for value in VALUES + ('plain text',)
        for template in (
            'title:\n  VALUE\nfocus: none',
            'metadata:\n  title:\n    VALUE\n  owner: local\nfocus: none',
            'authors:\n  -\n    VALUE\n  - other\nfocus: none',
            'authors:\n-\n  VALUE\n- other\nfocus: none',
            'authors:\n  - title:\n      VALUE\n    owner: local\n  - name: other\nfocus: none',
        )
    )

    def test_standalone_orphan_scalars_and_flows_cannot_grant_authority(self):
        for declaration in self.INVALID_ORPHANS:
            self.assert_invalid_parent(declaration)

    def test_completed_next_line_nodes_cannot_accept_more_values(self):
        for declaration in self.COMPLETED_SCALARS:
            self.assert_invalid_parent(declaration)

    def test_malformed_standalone_nodes_fail_all_cli_consumers(self):
        declarations = self.INVALID_ORPHANS[::3] + self.COMPLETED_SCALARS[::9]
        for declaration in declarations:
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli(declaration, check)
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn('official (9/10)', result.stdout)

    def test_property_rows_do_not_establish_container_indentation(self):
        for declaration in self.PROPERTY_CONTROLS:
            with self.subTest(declaration=declaration):
                metadata = vr.validated_metadata(self.report(declaration))
                self.assertIsNone(vr.metadata_problem(metadata))
                self.assertEqual(metadata['focus'], [])
                self.assertEqual(metadata['depth'], '')
                video = self.report(declaration, 'https://youtube.com/example [YT]\n')
                self.assertNotIn('official (9/10)', '\n'.join(vr.check_sources(video)[1]))
                for check in (vr.check_focus, vr.check_structure, vr.check_process):
                    self.assertNotEqual(check(self.report(declaration))[0], 'FAIL')
                self.assertEqual(vr.check_citations(video, fetch=lambda *args: 200)[0], 'PASS')

    def test_pending_scalar_and_sequence_siblings_remain_valid(self):
        for declaration in self.SCALAR_CONTROLS:
            with self.subTest(declaration=declaration):
                metadata = vr.validated_metadata(self.report(declaration))
                self.assertIsNone(vr.metadata_problem(metadata))
                self.assertEqual(metadata['focus'], [])
                self.assertEqual(metadata['depth'], '')
                self.assertNotEqual(vr.check_structure(self.report(declaration))[0], 'FAIL')

    def test_valid_standalone_nodes_pass_cli_consumers(self):
        declarations = self.PROPERTY_CONTROLS[::3] + self.PROPERTY_CONTROLS[-8:] + self.SCALAR_CONTROLS[::5]
        for declaration in declarations:
            for check in ('focus', 'structure', 'process', 'sources', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)




class Final194FlowSeparators(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    BAD_ENTRIES = ('[,one]', '[one,,two]', '[one, ,two]', '[,]', '[,,]',
                   '[one,,]', '{,a: b}', '{a: b,,c: d}', '{a: b, ,c: d}',
                   '{,}', '{a: b,,}', '{a: b: c}', '{a: : c}',
                   '{"a":"b": "c"}', '[a: b: c]', '[a: : c]',
                   '{: value}', '[: value]', '{a: [],,b: {}}',
                   '[[], , {}]', '{a: [one,,two]}', '[{a: b: c}]')
    HELD_OUT_BAD = ('[[,]]', '[one, [two, ,three]]',
                    '{a: {b: c: d}, e: []}', '[{a: b},, {c: d}]',
                    '{a: ["comma,inside",, "tail"]}',
                    '{a: ["colon: inside"], b: c: d}',
                    '{a: &note "quoted": extra}', '{a: b, : value}',
                    '[one, : value]', '{a: [one,],,}')
    VALID = ('[]', '{}', '[one,]', '{a: b,}', '[one, two, ]',
             '{a: b, c: d, }', '{a: }', '{a: , b: }', '[a: ]',
             '{a, b}', '[{}, [], {a: [one, two,], b: },]',
             '{"a":"b", "empty":null}', '["comma,,inside", "colon: : inside"]',
             "{'a': 'it''s, fine: now'}", '[&note one, two]',
             '{a: &note one, b: two}', '[&note, two]',
             '{a: [one,], b: {c: ,},}', '[a: b, c: d]',
             '{a: "", b: [], c: {}, d: }')
    HELD_OUT_VALID = ('[[one,], {a: [two,], b: },]',
                      '{a: {b: , c: [three,]}, d: []}',
                      '["[not,a,flow]", "{not:a:map}"]',
                      '[!!str word, !<tag:yaml.org,2002:str> other]',
                      '{"a":1, "b":true, "c":[]}',
                      '{a: [one], b: {c}, d: }')
    PLAIN_COLON_CONTROLS = ('[url:example, 12:34]', '{a: url:example, b: 12:34}',
                            '{url:example, 12:34}', 'plain:url, 12:34')
    FOCUS_CONTROLS = ('focus: security, devtools', 'focus: #security, #devtools',
                      'focus: [security, devtools, ]', 'focus: [ - , security ]',
                      'focus: -, security', 'focus: []', 'focus: none')

    def test_missing_entries_and_repeated_colons_fail_all_direct_consumers(self):
        for value in self.BAD_ENTRIES + self.HELD_OUT_BAD:
            for row in ('metadata: VALUE', 'metadata:\n  note: VALUE', 'authors:\n  - note: VALUE'):
                self.assert_invalid_parent(row.replace('VALUE', value) + '\nfocus: content')

    def test_malformed_separators_fail_before_all_cli_consumers(self):
        for value in self.BAD_ENTRIES[::3] + self.HELD_OUT_BAD[::2]:
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(value=value, check=check):
                    result = self.cli('metadata: ' + value + '\nfocus: content', check)
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn('official (9/10)', result.stdout)

    def test_valid_flow_separators_and_empty_values_remain_supported(self):
        for value in self.VALID + self.HELD_OUT_VALID + self.PLAIN_COLON_CONTROLS:
            with self.subTest(value=value):
                declaration = 'metadata: ' + value + '\nfocus: none'
                content = self.report(declaration, 'https://youtube.com/example [YT]\n')
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(content)))
                self.assertEqual(vr.declared_focus(content), [])
                self.assertNotIn('official (9/10)', '\n'.join(vr.check_sources(content)[1]))
                self.assertEqual(vr.check_citations(content, fetch=lambda *args: 200)[0], 'PASS')
                for check in (vr.check_focus, vr.check_structure, vr.check_process):
                    self.assertNotEqual(check(self.report(declaration))[0], 'FAIL')

    def test_valid_flow_controls_pass_cli_consumers(self):
        for value in self.VALID[::3] + self.HELD_OUT_VALID + self.PLAIN_COLON_CONTROLS:
            for check in ('focus', 'structure', 'process', 'sources', 'all'):
                with self.subTest(value=value, check=check):
                    self.assertEqual(self.cli('metadata: ' + value + '\nfocus: none', check).returncode, 0)

    def test_focus_csv_shorthand_and_nonempty_flow_lists_remain_supported(self):
        for declaration in self.FOCUS_CONTROLS:
            with self.subTest(declaration=declaration):
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration))))
                self.assertEqual(self.cli(declaration, 'all').returncode, 0)
        for value in ('[,security]', '[security,,devtools]', '[security, ,devtools]'):
            self.assert_invalid_parent('focus: ' + value)




class Final195QuotedKeyIdentity(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    LITERAL_KEYS = tuple(
        outer + inner * count + name + inner * count + outer
        for name in ('focus', 'depth')
        for outer, inner in (("\"", "'"), ("'", "\""))
        for count in (1, 2)
    ) + ('"\'focus"', '"focus\'"')
    BAD_VALUES = ('"first", "second"', '[first], [second]')
    PLAIN_VALUES = ("Design trends, '90s revival", 'Design trends, "unfinished quotation')

    def test_literal_reserved_key_does_not_receive_focus_csv_permission(self):
        for key in self.LITERAL_KEYS:
            for value in self.BAD_VALUES:
                self.assert_invalid_parent(key + ': ' + value + '\nfocus: content')

    def test_malformed_literal_key_fails_all_cli_consumers(self):
        for key in self.LITERAL_KEYS:
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(key=key, check=check):
                    result = self.cli(key + ': "first", "second"\nfocus: content', check)
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn('official (9/10)', result.stdout)

    def test_literal_quoted_keys_preserve_foreign_plain_punctuation(self):
        for key in self.LITERAL_KEYS:
            for value in self.PLAIN_VALUES:
                declaration = key + ': ' + value + '\nfocus: none\ndepth: default'
                with self.subTest(key=key, value=value):
                    metadata = vr.validated_metadata(self.report(declaration))
                    self.assertIsNone(vr.metadata_problem(metadata))
                    self.assertEqual(metadata['focus'], [])
                    self.assertEqual(metadata['depth'], 'default')
                    video = self.report(declaration, 'https://youtube.com/example [YT]\n')
                    self.assertNotIn('official (9/10)', '\n'.join(vr.check_sources(video)[1]))
                    self.assertEqual(vr.check_citations(video, fetch=lambda *args: 200)[0], 'PASS')
                    for check in ('focus', 'structure', 'process', 'sources', 'all'):
                        self.assertEqual(self.cli(declaration, check).returncode, 0)

    def test_exact_single_layer_reserved_keys_keep_their_identity(self):
        for focus_key in ('focus', "'focus'", '"focus"'):
            for depth_key in ('depth', "'depth'", '"depth"'):
                declaration = focus_key + ': security, devtools\n' + depth_key + ': default'
                with self.subTest(focus_key=focus_key, depth_key=depth_key):
                    metadata = vr.validated_metadata(self.report(declaration))
                    self.assertIsNone(vr.metadata_problem(metadata))
                    self.assertEqual(metadata['focus'], ['security', 'devtools'])
                    self.assertEqual(metadata['depth'], 'default')
                    self.assertEqual(self.cli(declaration, 'all').returncode, 0)
        for key in self.LITERAL_KEYS:
            declaration = key + ': deep'
            with self.subTest(key=key):
                metadata = vr.validated_metadata(self.report(declaration))
                self.assertIsNone(vr.metadata_problem(metadata))
                self.assertEqual(metadata['focus'], [])
                self.assertEqual(metadata['depth'], '')
                self.assertEqual(self.cli(declaration, 'all').returncode, 0)




class Final195FlowColonBoundaries(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    BAD_VALUES = ('{a: b:}', '[a: b:]', '{a: b:, c: d}', '[a: b:, c]',
                  '{a: b:[]}', '{a: b:{}}', '{a: [b: c:]}',
                  '[{a: b:}, {c: d}]', '{:}', '[:]', '{:[]}',
                  '{a: [b: c:, d], e: f}')
    CONTROLS = ('{a:}', '[a:]', '{a:, b: c}', '{a:[]}', '{a:{b: c}}',
                '{a: [b:, c:]}', '{a: url:example, b: 12:34}',
                '[url:example, 12:34]', '{a: "b:}", c: "d:,"}',
                '["a:}", "b:]", "c:,", "d:[]"]')

    def test_flow_delimiters_bound_colons_before_all_direct_consumers(self):
        for value in self.BAD_VALUES:
            self.assert_invalid_parent('metadata: ' + value + '\nfocus: content')

    def test_flow_colon_boundaries_fail_all_cli_consumers(self):
        for value in self.BAD_VALUES:
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(value=value, check=check):
                    result = self.cli('metadata: ' + value + '\nfocus: content', check)
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn('official (9/10)', result.stdout)

    def test_empty_values_nested_flows_and_literal_colons_remain_supported(self):
        for value in self.CONTROLS:
            declaration = 'metadata: ' + value + '\nfocus: none'
            with self.subTest(value=value):
                metadata = vr.validated_metadata(self.report(declaration))
                self.assertIsNone(vr.metadata_problem(metadata))
                self.assertEqual(metadata['focus'], [])
                video = self.report(declaration, 'https://youtube.com/example [YT]\n')
                self.assertNotIn('official (9/10)', '\n'.join(vr.check_sources(video)[1]))
                self.assertEqual(vr.check_citations(video, fetch=lambda *args: 200)[0], 'PASS')
                for check in ('focus', 'structure', 'process', 'sources', 'all'):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)




class Final196BlockHeaderGrammar(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    BAD_SUFFIXES = ('0', '10', '01', '00', '++', '--', '+-', '-+',
                    '+0', '0+', '-0', '0-', '2++', '++2', '2+-', '2-+',
                    '+2+', '-2-', 'garbage', '2garbage', ' 2', '+ 2', '#comment')
    BAD_HEADERS = tuple("|" + suffix for suffix in BAD_SUFFIXES) + tuple(">" + suffix for suffix in BAD_SUFFIXES)
    GOOD_SUFFIXES = ('', '+', '-') + tuple(
        form.replace('N', str(number))
        for number in range(1, 10)
        for form in ('N', '+N', '-N', 'N+', 'N-')
    )
    GOOD_HEADERS = tuple("|" + suffix for suffix in GOOD_SUFFIXES) + tuple(">" + suffix for suffix in GOOD_SUFFIXES)
    FinalES = ('title: HEADER', 'title: &note !!str HEADER', 'title:\n  &note\n  HEADER',
                'metadata:\n  title: HEADER', 'authors:\n  - &note HEADER')

    def test_malformed_block_headers_fail_before_all_direct_consumers(self):
        for header in self.BAD_HEADERS:
            for prefix in self.FinalES:
                self.assert_invalid_parent(prefix.replace('HEADER', header) + '\nfocus: content')

    def test_malformed_block_header_cli_paths_cannot_grant_authority(self):
        for header in ('|0', '>10', '|garbage', '>++2', '|2+-', '>-0', '|#comment', '> 2'):
            for prefix in (self.FinalES[0], self.FinalES[1], self.FinalES[2]):
                for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                    with self.subTest(header=header, prefix=prefix, check=check):
                        result = self.cli(prefix.replace('HEADER', header) + '\nfocus: content', check)
                        self.assertEqual(result.returncode, 1)
                        self.assertNotIn('official (9/10)', result.stdout)

    def test_all_supported_block_indicators_preserve_inert_content(self):
        for header in self.GOOD_HEADERS:
            for prop in ('', '&note !!str '):
                declaration = 'title: ' + prop + header + '\t# ordinary comment\n         |0 >10\nfocus: none'
                with self.subTest(header=header, prop=prop):
                    metadata = vr.validated_metadata(self.report(declaration))
                    self.assertIsNone(vr.metadata_problem(metadata))
                    self.assertEqual(metadata['focus'], [])
                    self.assertEqual(metadata['depth'], '')
                    self.assertNotEqual(vr.check_structure(self.report(declaration))[0], 'FAIL')
                    video = self.report(declaration, 'https://youtube.com/example [YT]\n')
                    self.assertNotIn('official (9/10)', '\n'.join(vr.check_sources(video)[1]))
                    self.assertEqual(vr.check_citations(video, fetch=lambda *args: 200)[0], 'PASS')

    def test_valid_block_headers_and_properties_pass_cli_consumers(self):
        for header in ('|', '>-', '|9', '>+2', '|-2', '>2-'):
            for declaration in (
                    'title: &note !!str ' + header + '\n         text\nfocus: none',
                    'title:\n  &note\n  ' + header + '\n         text\nfocus: none',
                    'authors:\n  - !<tag:yaml.org,2002:str> ' + header + '\n           text\nfocus: none'):
                for check in ('focus', 'structure', 'process', 'sources', 'all'):
                    with self.subTest(declaration=declaration, check=check):
                        self.assertEqual(self.cli(declaration, check).returncode, 0)

    def test_quoted_and_nonleading_indicator_text_remains_literal(self):
        for header in self.BAD_HEADERS:
            for literal in ('"' + header + '"', "'" + header + "'", 'plain ' + header):
                declaration = 'title: &note ' + literal + '\nfocus: none'
                with self.subTest(literal=literal):
                    self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration))))
                    self.assertEqual(vr.declared_focus(self.report(declaration)), [])
        for declaration in ('title: "|0"\nfocus: none', "title: !!str '>10'\nfocus: none",
                            'title: plain |garbage\nfocus: none', 'title: |\n  >10 |0\nfocus: none'):
            for check in ('focus', 'structure', 'process', 'sources', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)




class Final196FlowBlockIndicators(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    BAD_VALUES = tuple(
        wrapper.replace('HEADER', header)
        for header in ('|0', '>10', '|garbage', '>+-', '|', '>2-')
        for wrapper in ('[HEADER]', '{title: HEADER}', '[&note !!str HEADER]',
                        '{nested: [safe, {title: &note HEADER}]}')
    )
    CONTROLS = ('["|0", ">10"]', "{'title': '|garbage'}", '[&note "|0"]',
                '{nested: [safe, {title: &note ">"}]}', '[plain |0, plain >10]',
                '{title: a|garbage, note: x>10}', '["|", ">2-"]')

    def test_flow_block_markers_fail_before_all_direct_consumers(self):
        for value in self.BAD_VALUES:
            self.assert_invalid_parent('metadata: ' + value + '\nfocus: content')

    def test_flow_block_markers_fail_all_cli_consumers(self):
        for value in self.BAD_VALUES:
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(value=value, check=check):
                    result = self.cli('metadata: ' + value + '\nfocus: content', check)
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn('official (9/10)', result.stdout)

    def test_quoted_and_nonleading_flow_markers_remain_data(self):
        for value in self.CONTROLS:
            declaration = 'metadata: ' + value + '\nfocus: none'
            with self.subTest(value=value):
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration))))
                video = self.report(declaration, 'https://youtube.com/example [YT]\n')
                self.assertNotIn('official (9/10)', '\n'.join(vr.check_sources(video)[1]))
                self.assertEqual(vr.check_citations(video, fetch=lambda *args: 200)[0], 'PASS')
                for check in ('focus', 'structure', 'process', 'sources', 'all'):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)



class Final197UnmatchedClosers(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    BAD_DECLARATIONS = tuple(
        template.replace('VALUE', value)
        for value in (']', '}', '] trailing', '} trailing', '&note ]', '!!str }', '&note !!str ]')
        for template in ('title: VALUE', 'title:\n  VALUE', 'metadata:\n  title: VALUE', 'authors:\n  - VALUE')
    )
    CONTROLS = ('title: "]"', "title: '}'", 'title: &note !!str "]"',
                'title: text ] }', 'title: a]b}c', 'title: []', 'title: {}',
                'title: ["]", "}"]', 'title: {note: "]"}',
                'title: |\n  ] }', 'authors:\n  - "]"')

    def test_unmatched_closers_reject_before_direct_consumers_and_fetch(self):
        for declaration in self.BAD_DECLARATIONS:
            self.assert_invalid_parent(declaration + '\nfocus: content')

    def test_unmatched_closers_reject_all_cli_checks(self):
        for declaration in self.BAD_DECLARATIONS:
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli(declaration + '\nfocus: content', check)
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn('official (9/10)', result.stdout)

    def test_quoted_nonleading_and_balanced_delimiters_remain_data(self):
        for declaration in self.CONTROLS:
            declaration += '\nfocus: none'
            with self.subTest(declaration=declaration):
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration))))
                video = self.report(declaration, 'https://youtube.com/example [YT]\n')
                self.assertNotIn('official (9/10)', '\n'.join(vr.check_sources(video)[1]))
                self.assertEqual(vr.check_citations(video, fetch=lambda *args: 200)[0], 'PASS')
                for check in ('focus', 'structure', 'process', 'sources', 'all'):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)


class Final197CustomManifestHashtags(unittest.TestCase):
    report = Final184Test.report
    CUSTOM = {'tags': {'custom-lens': {'addendum': 'Custom lens evidence', 'source_tags': ['YT'],
                                     'authorities': ['youtube.com']}},
              'bundles': {'custom-bundle': ['custom-lens']}}
    BAD_DECLARATIONS = tuple(
        form.replace('TOKEN', token)
        for token in ('custom-lens', 'custom-bundle')
        for form in ('focus: #TOKEN review', 'focus: #TOKEN\treview',
                     'focus: #TOKEN review\n  - none', 'focus: #TOKEN\n  - none')
    )

    def test_custom_reserved_hashtags_cannot_silently_erase_focus(self):
        for declaration in self.BAD_DECLARATIONS:
            report = self.report(declaration)
            metadata = vr.validated_metadata(report, self.CUSTOM)
            with self.subTest(declaration=declaration, check='problem'):
                self.assertIsNotNone(vr.metadata_problem(metadata))
            with self.subTest(declaration=declaration, check='no_authority'):
                self.assertEqual(metadata['focus'], [])
            for kwargs in ({'manifest': self.CUSTOM}, {'manifest': self.CUSTOM, '_metadata': metadata}):
                with self.subTest(declaration=declaration, check='focus', prevalidated='_metadata' in kwargs):
                    self.assertEqual(vr.check_focus(report, **kwargs)[0], 'FAIL')

    def test_valid_custom_tags_and_bundles_still_require_their_addendum(self):
        for token in ('custom-lens', 'custom-bundle'):
            for form in ('focus: TOKEN', 'focus: #TOKEN', 'focus: [TOKEN]',
                         'focus: "TOKEN"', 'focus:\n  - TOKEN'):
                declaration = form.replace('TOKEN', token)
                report = self.report(declaration)
                with self.subTest(declaration=declaration):
                    metadata = vr.validated_metadata(report, self.CUSTOM)
                    self.assertIsNone(vr.metadata_problem(metadata))
                    self.assertEqual(metadata['focus'], ['custom-lens'])
                    self.assertEqual(vr.check_focus(report, self.CUSTOM)[0], 'FAIL')
                    complete = report + '\n## Custom lens evidence\nSource [YT].\n'
                    self.assertEqual(vr.check_focus(complete, self.CUSTOM)[0], 'PASS')

    def test_custom_manifest_preserves_comments_and_does_not_leak_to_default(self):
        for declaration in ('focus: # ordinary note', 'focus: #unknown-note review',
                            'focus: # ordinary note\n  - none', 'focus: none',
                            'focus: # ordinary note\n  - custom-lens'):
            with self.subTest(declaration=declaration):
                report = self.report(declaration)
                metadata = vr.validated_metadata(report, self.CUSTOM)
                self.assertIsNone(vr.metadata_problem(metadata))
                self.assertEqual(metadata['focus'], ['custom-lens'] if declaration.endswith('custom-lens') else [])
        report = self.report('focus: #custom-lens review')
        self.assertIsNone(vr.metadata_problem(vr.validated_metadata(report)))
        self.assertEqual(vr.check_focus(report)[0], 'PASS')

    def test_configured_manifest_cli_rejects_ambiguous_tags_and_bundles(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / 'tags.json'
            manifest.write_text(json.dumps(self.CUSTOM))
            script = Path(vr.__file__).resolve()
            for declaration in self.BAD_DECLARATIONS:
                report = Path(tmp) / 'report.md'
                report.write_text(self.report(declaration))
                for check in ('focus', 'structure', 'all'):
                    with self.subTest(declaration=declaration, check=check):
                        result = subprocess.run([sys.executable, str(script), check, str(report), '--offline'],
                                                capture_output=True, text=True, timeout=10,
                                                env={'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1',
                                                     'RESEARCH_STACK_FOCUS': str(manifest)})
                        self.assertEqual(result.returncode, 1)


class Final197ReservedNodeStarts(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    BAD_VALUES = tuple(value for symbol in (',', '%', '@', '`')
                       for value in (symbol, symbol + 'token', '&note ' + symbol, '!!str ' + symbol + 'token'))

    def test_reserved_node_starts_fail_before_authority_and_fetch(self):
        for value in self.BAD_VALUES:
            for template in ('title: VALUE', 'title:\n  VALUE', 'metadata:\n  title: VALUE', 'authors:\n  - VALUE'):
                self.assert_invalid_parent(template.replace('VALUE', value) + '\nfocus: content')

    def test_reserved_node_starts_fail_all_cli_consumers(self):
        for symbol in (',', '%', '@', '`'):
            for value in (symbol, '&note !!str ' + symbol + 'token'):
                for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                    with self.subTest(value=value, check=check):
                        result = self.cli('title: ' + value + '\nfocus: content', check)
                        self.assertEqual(result.returncode, 1)
                        self.assertNotIn('official (9/10)', result.stdout)

    def test_quoted_and_nonleading_reserved_symbols_remain_literal(self):
        for symbol in (',', '%', '@', '`'):
            for value in ('"' + symbol + 'token"', "'" + symbol + "token'", 'plain ' + symbol + 'token', 'a' + symbol + 'b'):
                declaration = 'title: &note !!str ' + value + '\nfocus: none'
                with self.subTest(value=value):
                    self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration))))
                    video = self.report(declaration, 'https://youtube.com/example [YT]\n')
                    self.assertNotIn('official (9/10)', '\n'.join(vr.check_sources(video)[1]))
                    self.assertEqual(vr.check_citations(video, fetch=lambda *args: 200)[0], 'PASS')
                    for check in ('focus', 'structure', 'process', 'sources', 'all'):
                        self.assertEqual(self.cli(declaration, check).returncode, 0)


class Final197EscapedMappingKeys(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    FinalES = ('metadata:\n  ', 'metadata:\n  inner:\n    ', 'authors:\n  - ',
                'authors:\n- ', 'authors:\n  - &node !!map ', 'authors:\n  - - ',
                'authors:\n  - title: safe\n    ')
    KEYS = ('"note\\": safe', '"note\\\\": safe')

    def test_escaped_nested_mapping_keys_fail_before_authority_and_fetch(self):
        for prefix in self.FinalES:
            for key in self.KEYS:
                self.assert_invalid_parent(prefix + key + '\nfocus: content #"')

    def test_escaped_nested_mapping_keys_fail_all_cli_consumers(self):
        for prefix in self.FinalES:
            for key in self.KEYS:
                declaration = prefix + key + '\nfocus: content #"'
                for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                    with self.subTest(prefix=prefix, key=key, check=check):
                        result = self.cli(declaration, check)
                        self.assertEqual(result.returncode, 1)
                        self.assertNotIn('official (9/10)', result.stdout)

    def test_root_escape_refusal_and_plain_quoted_keys_remain_supported(self):
        for key in self.KEYS:
            self.assert_invalid_parent(key + '\nfocus: content #"')
        for prefix in self.FinalES:
            for key in ('"note": safe', "'note': safe", 'note: "quoted \\" value"', 'note: text " quote'):
                declaration = prefix + key + '\nfocus: none'
                with self.subTest(prefix=prefix, key=key):
                    self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration))))
                    for check in ('focus', 'structure', 'process', 'sources', 'all'):
                        self.assertEqual(self.cli(declaration, check).returncode, 0)


class Final197QuotedEscapeGrammar(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    BAD_ESCAPES = (r'\q', r'\xZZ', r'\uZZZZ', r'\UZZZZZZZZ', r'\x0', r'\u123',
                   r'\U1234567', r'\x0G', r'\u12G4', r'\U0000000G', r'\z')
    SHAPES = ('title: VALUE', 'title: &note !!str VALUE', 'metadata:\n  title: VALUE',
              'authors:\n  - VALUE', 'metadata: {note: [VALUE]}')
    GOOD_ESCAPES = ('0', 'a', 'b', 't', '\t', 'n', 'v', 'f', 'r', 'e', ' ', '"', '/',
                    '\\', 'N', '_', 'L', 'P', 'x41', 'u0041', 'U00000041')

    def test_malformed_quoted_escapes_fail_before_authority_and_fetch(self):
        for escape in self.BAD_ESCAPES:
            for shape in self.SHAPES:
                self.assert_invalid_parent(shape.replace('VALUE', '"' + escape + '"') + '\nfocus: content')

    def test_malformed_quoted_escapes_fail_all_cli_consumers(self):
        for escape in (r'\q', r'\xZZ', r'\uZZZZ', r'\UZZZZZZZZ'):
            for shape in self.SHAPES:
                for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                    with self.subTest(escape=escape, shape=shape, check=check):
                        result = self.cli(shape.replace('VALUE', '"' + escape + '"') + '\nfocus: content', check)
                        self.assertEqual(result.returncode, 1)
                        self.assertNotIn('official (9/10)', result.stdout)

    def test_yaml_escapes_single_quotes_and_plain_backslashes_remain_supported(self):
        values = tuple('"\\' + code + '"' for code in self.GOOD_ESCAPES) + (
            r"'\q'", r'plain \q', r'path\xZZ', '"a\\\\q"')
        for value in values:
            for shape in ('title: &note !!str VALUE', 'metadata: {note: [VALUE]}'):
                declaration = shape.replace('VALUE', value) + '\nfocus: none'
                with self.subTest(value=value, shape=shape):
                    self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration))))
                    video = self.report(declaration, 'https://youtube.com/example [YT]\n')
                    self.assertNotIn('official (9/10)', '\n'.join(vr.check_sources(video)[1]))
                    self.assertEqual(vr.check_citations(video, fetch=lambda *args: 200)[0], 'PASS')
                    for check in ('focus', 'structure', 'process', 'sources', 'all'):
                        self.assertEqual(self.cli(declaration, check).returncode, 0)

class Final197AliasBoundary(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    DECLARATIONS = ('title: *missing', 'metadata:\n  title: *missing', 'authors:\n  - *missing',
                    'metadata: [*missing]', 'metadata: {note: *missing}', 'title: &note *missing',
                    'title: &note safe\nother: *note', 'title: &note safe\nmetadata: [*note]')

    def test_alias_nodes_are_explicitly_unsupported_before_authority_and_fetch(self):
        for declaration in self.DECLARATIONS:
            self.assert_invalid_parent(declaration + '\nfocus: content')

    def test_alias_nodes_are_rejected_by_all_cli_consumers(self):
        for declaration in self.DECLARATIONS:
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli(declaration + '\nfocus: content', check)
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn('official (9/10)', result.stdout)

    def test_quoted_and_nonleading_asterisks_and_anchor_nodes_remain_supported(self):
        for declaration in ('title: "*missing"', "title: '*missing'", 'title: plain *missing',
                            'title: a*b', 'title: &note safe', 'metadata: ["*missing", a*b]',
                            'title:\n  &note\n  safe'):
            declaration += '\nfocus: none'
            with self.subTest(declaration=declaration):
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration))))
                for check in ('focus', 'structure', 'process', 'sources', 'all'):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)

class Final197UnicodeEscapeRange(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent

    def test_out_of_unicode_range_escapes_fail_before_authority_and_fetch(self):
        for escape in (r'\U00110000', r'\UFFFFFFFF'):
            for shape in ('title: VALUE', 'title: &note VALUE', 'metadata: {note: [VALUE]}'):
                declaration = shape.replace('VALUE', '"' + escape + '"') + '\nfocus: content'
                self.assert_invalid_parent(declaration)
                for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                    with self.subTest(escape=escape, shape=shape, check=check):
                        result = self.cli(declaration, check)
                        self.assertEqual(result.returncode, 1)
                        self.assertNotIn('official (9/10)', result.stdout)

    def test_valid_unicode_range_boundaries_and_bmp_escapes_remain_supported(self):
        for escape in (r'\U0010FFFF', r'\U00000041', r'\u03A9', r'\x41'):
            for shape in ('title: VALUE', 'title: &note VALUE', 'metadata: {note: [VALUE]}'):
                declaration = shape.replace('VALUE', '"' + escape + '"') + '\nfocus: none'
                with self.subTest(escape=escape, shape=shape):
                    self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration))))
                    for check in ('focus', 'structure', 'process', 'sources', 'all'):
                        self.assertEqual(self.cli(declaration, check).returncode, 0)

class Final197EmptyManifestDefault(unittest.TestCase):
    report = Final184Test.report

    def test_explicit_empty_manifest_retains_existing_default_semantics(self):
        for declaration in ('focus: content', 'focus: #content review', 'focus: none',
                            'focus: #unknown-lens review', 'focus: #content\n  - none'):
            report = self.report(declaration)
            with self.subTest(declaration=declaration):
                self.assertEqual(vr.validated_metadata(report, {}), vr.validated_metadata(report))
                self.assertEqual(vr.check_focus(report, {}), vr.check_focus(report))
        self.assertEqual(vr.expand_focus(['content'], {}), vr.expand_focus(['content']))


class Final198NodeGrammar(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    BAD_PROPERTIES = ('&', '& safe', '&[]', '!<> safe', '!< safe', '!<tag safe',
                      '!! safe', '!name! safe', '!tag%GG safe', '!<tag%ZZ> safe',
                      '&one &two safe', '!one !two safe')
    BAD_DASHES = ('-', '- # note', '-\t# note')
    SHAPES = ('title: VALUE', 'metadata:\n  title: VALUE', 'authors:\n  - title: VALUE',
              'metadata: {title: VALUE}', 'metadata: [VALUE]')

    def test_malformed_properties_fail_before_authority_and_fetch(self):
        for value in self.BAD_PROPERTIES:
            for shape in self.SHAPES:
                self.assert_invalid_parent(shape.replace('VALUE', value) + '\nfocus: content')
        self.assert_invalid_parent('title: & "Notes\nfocus: content #"')

    def test_property_failures_reach_every_cli_gate(self):
        for declaration in ('title: & "Notes\nfocus: content #"', 'title: !<> safe\nfocus: content',
                            'authors:\n  - &one &two safe\nfocus: content', 'metadata: [!! safe]\nfocus: content'):
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    self.assertEqual(self.cli(declaration, check).returncode, 1)

    def test_supported_properties_and_literal_indicators_remain_valid(self):
        for value in ('&note safe', '! safe', '!!str safe', '!local safe', '!h!thing safe',
                      '!<tag:yaml.org,2002:str> safe', '!encoded%20name safe',
                      '&note !!str safe', '!!str &note safe', '"&"', "'!<bad'", 'plain & !'):
            declaration = 'title: ' + value + '\nfocus: none'
            with self.subTest(value=value):
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration))))
                self.assertEqual(self.cli(declaration, 'all').returncode, 0)

    def test_foreign_dash_indicators_fail_before_authority_and_fetch(self):
        for value in self.BAD_DASHES:
            for shape in self.SHAPES[:3]:
                self.assert_invalid_parent(shape.replace('VALUE', value) + '\nfocus: content')
        for declaration in ('metadata:\n  focus: -', 'metadata:\n  depth: -',
                            'metadata: {title: -}', 'metadata: [-]', 'title: &note -'):
            self.assert_invalid_parent(declaration + '\nfocus: content')

    def test_foreign_dash_failures_reach_every_cli_gate(self):
        for declaration in ('title: -', 'title: - # note', 'metadata:\n  depth: -', 'metadata: {title: -}'):
            for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    self.assertEqual(self.cli(declaration + '\nfocus: content', check).returncode, 1)

    def test_root_sentinels_and_literal_dashes_remain_valid(self):
        for declaration in ('focus: -', 'focus: - # note', 'depth: -\nfocus: none',
                            'depth: - # note\nfocus: none', 'focus: [-, -]', 'focus: [ - , - ]',
                            'title: "-"\nfocus: none', "title: '-'\nfocus: none",
                            'title: -word\nfocus: none', 'authors:\n  -\nfocus: none'):
            with self.subTest(declaration=declaration):
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration))))
                self.assertEqual(vr.declared_focus(self.report(declaration)), [])
                self.assertEqual(self.cli(declaration, 'all').returncode, 0)


class Final198RawCharacters(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    BAD = tuple(chr(i) for i in range(32) if i not in (9, 10, 13)) + tuple(chr(i) for i in range(127,160)) + ('\ufffe', '\uffff')

    def test_forbidden_raw_header_characters_fail_before_authority_and_fetch(self):
        for char in self.BAD:
            for shape in ('title: "badCHARvalue"', 'title: badCHARvalue', 'title: |\n  badCHARvalue'):
                self.assert_invalid_parent(shape.replace('CHAR', char) + '\nfocus: content')
        for char in ('\ud800', '\udfff'):
            self.assert_invalid_parent('title: "bad' + char + 'value"\nfocus: content')

    def test_raw_character_failures_reach_every_file_cli_gate(self):
        for char in ('\0', '\x01', '\x1f', '\x7f', '\x9f', '\ufffe'):
            for shape in ('title: "badCHARvalue"', 'title: |\n  badCHARvalue'):
                for check in ('focus', 'structure', 'process', 'sources', 'citations', 'all'):
                    with self.subTest(codepoint=ord(char), shape=shape, check=check):
                        self.assertEqual(self.cli(shape.replace('CHAR', char) + '\nfocus: content', check).returncode, 1)

    def test_supported_printable_and_escaped_characters_remain_valid(self):
        for value in ('"tab\tvalue"', '"\u00a0\ud7ff\ue000\ufffd\U0010ffff"',
                      r'"\0\a\x1f\x7f\u009f"', '"ordinary"'):
            declaration = 'title: ' + value + '\nfocus: none'
            with self.subTest(value=repr(value)):
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration))))
                self.assertEqual(self.cli(declaration, 'all').returncode, 0)


class Final198DecodedIdentity(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli

    def test_focus_hex_escapes_are_identical_to_their_declared_lens(self):
        for spelling in (r'\x73ecurity', r'\u0073ecurity', r'\U00000073ecurity',
                         r'\x73\x65\x63\x75\x72\x69\x74\x79'):
            for form in ('focus: "VALUE"', 'focus: ["VALUE"]', 'focus:\n  - "VALUE"'):
                declaration = form.replace('VALUE', spelling)
                with self.subTest(declaration=declaration):
                    metadata = vr.validated_metadata(self.report(declaration))
                    self.assertIsNone(vr.metadata_problem(metadata))
                    self.assertEqual(metadata['focus'], ['security'])
                    self.assertEqual(vr.check_focus(self.report(declaration))[0], 'PASS')
                    missing = self.report(declaration, '## Decision answer\nSource [YT].\n')
                    self.assertEqual(vr.check_focus(missing)[0], 'FAIL')
                    for check in ('focus', 'structure', 'all'):
                        self.assertEqual(self.cli(declaration, check).returncode, 0)

    def test_depth_hex_escapes_preserve_deep_process_requirements(self):
        for spelling in (r'\x64eep', r'\u0064eep', r'\U00000064eep', r'\x64\x65\x65\x70'):
            declaration = 'depth: "' + spelling + '"\nfocus: none'
            with self.subTest(spelling=spelling):
                metadata = vr.validated_metadata(self.report(declaration))
                self.assertIsNone(vr.metadata_problem(metadata))
                self.assertEqual(metadata['depth'], 'deep')
                missing = self.report(declaration, 'Report without process dashboard.\n')
                self.assertEqual(vr.check_process(missing)[0], 'WARN')
                complete = missing + '\nPerspectives: 3\nAttribution: 1/1\nInternal round: complete\n'
                self.assertEqual(vr.check_process(complete)[0], 'PASS')
                for check in ('process', 'structure', 'all'):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)

    def test_valid_yaml_escape_alphabet_decodes_once(self):
        escapes = {'0':'\0','a':'\a','b':'\b','t':'\t','\t':'\t','n':'\n','v':'\v','f':'\f',
                   'r':'\r','e':'\x1b',' ':' ','"':'"','/':'/','\\':'\\','N':'\x85','_':'\xa0','L':'\u2028','P':'\u2029',
                   'x73':'s','u0073':'s','U00000073':'s'}
        for code, decoded in escapes.items():
            with self.subTest(code=code):
                self.assertEqual(vr.scalar_value('"\\' + code + '"'), decoded)
        for declaration in (r'focus: "\x6eone"', r'focus: "\U0000006eone"'):
            self.assertEqual(vr.declared_focus(self.report(declaration)), [])

    def test_decoded_focus_and_depth_identity_reaches_file_cli_gates(self):
        for declaration in (r'focus: "\x73ecurity"', r'focus: "\U00000073ecurity"',
                            r'depth: "\x64eep"', r'depth: "\U00000064eep"'):
            for check in ('focus', 'process', 'structure', 'all'):
                with self.subTest(declaration=declaration, check=check):
                    self.assertEqual(self.cli(declaration, check).returncode, 0)

    def test_single_quote_identity_and_literal_backslashes_stay_distinct(self):
        self.assertEqual(vr.scalar_value("'pilot''s'"), "pilot's")
        self.assertEqual(vr.scalar_value(r"'\x73ecurity'"), r'\x73ecurity')
        self.assertEqual(vr.scalar_value(r'\x73ecurity'), r'\x73ecurity')
        self.assertEqual(vr.scalar_value(r'"\\x73ecurity"'), r'\x73ecurity')
        manifest={'tags':{"pilot's":{'addendum':'Pilot evidence','source_tags':['YT']}},'bundles':{}}
        report=self.report("focus: 'pilot''s'", '## Pilot evidence\nSource [YT].\n')
        self.assertEqual(vr.validated_metadata(report,manifest)['focus'], ["pilot's"])
        self.assertEqual(vr.check_focus(report,manifest)[0], 'PASS')


class Final198FlowKeyRoles(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    BAD_VALUES = (r'{"na\u006de": safe}', r'["na\u006de": safe]',
                  r'{nested: {"na\x6de": safe}}', r'[safe, {"na\U0000006de": safe}]',
                  r'{"na\u006de"}', r'{"na\u006de", other: safe}',
                  r"{'na\me': safe}", r'{na\me: safe}', r'{["na\u006de"]: safe}')

    def test_flow_key_backslashes_fail_before_authority_and_fetch(self):
        for value in self.BAD_VALUES:
            self.assert_invalid_parent('metadata: '+value+'\nfocus: content')

    def test_flow_key_backslashes_fail_all_cli_gates(self):
        for value in self.BAD_VALUES[:4]:
            for check in ('focus','structure','process','sources','citations','all'):
                with self.subTest(value=value,check=check):
                    self.assertEqual(self.cli('metadata: '+value+'\nfocus: content',check).returncode,1)

    def test_escaped_values_and_ordinary_flow_keys_remain_supported(self):
        for value in (r'{name: "na\u006de"}', r'["na\x6de"]',
                      r'{nested: ["na\U0000006de"]}', r'[name: "va\x6cue"]',
                      r'{name: "one", other: "tw\u006f"}', "{'name': safe}"):
            declaration='metadata: '+value+'\nfocus: none'
            with self.subTest(value=value):
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration))))
                self.assertEqual(self.cli(declaration,'all').returncode,0)

class Final198SurrogateCompatibility(unittest.TestCase):
    def test_inherited_adjacent_u_surrogate_pair_identity_is_preserved(self):
        self.assertEqual(vr.scalar_value(r'"\uD83D\uDE00"'), '\U0001f600')
        self.assertEqual(vr.scalar_value(r'"\uD800"'), '\ud800')
        self.assertEqual(vr.scalar_value(r'"\uDC00"'), '\udc00')
        self.assertEqual(vr.scalar_value(r'"\\uD83D\\uDE00"'), r'\uD83D\uDE00')
        self.assertEqual(vr.scalar_value(r"'\uD83D\uDE00'"), r'\uD83D\uDE00')
        manifest = {'tags': {'\U0001f600': {'addendum': 'Emoji evidence', 'source_tags': ['YT']}}, 'bundles': {}}
        text = '---\nfocus: "\\uD83D\\uDE00"\n---\n## Emoji evidence\nSource [YT].\n'
        self.assertEqual(vr.validated_metadata(text, manifest)['focus'], ['\U0001f600'])
        self.assertEqual(vr.check_focus(text, manifest)[0], 'PASS')
        self.assertEqual(vr.check_focus(text.replace('## Emoji evidence', '## Missing evidence'), manifest)[0], 'FAIL')


class Final199PendingPropertyKinds(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    assert_invalid_parent = Final188ParentBoundary.assert_invalid_parent
    OWNERS = (
        ('title: ', '  '),
        ('metadata:\n  title: ', '    '),
        ('authors:\n  - ', '    '),
        ('authors:\n  - title: ', '      '),
        ('authors:\n  - &mapping title: ', '      '),
        ('authors:\n  - - ', '      '),
    )
    PROPERTY_PAIRS = (('&one', '&two'), ('!!str', '!local'), ('!local', '!!str'))

    def test_cross_row_duplicate_kinds_fail_all_direct_consumers_before_fetch(self):
        for owner, indent in self.OWNERS:
            for first, second in self.PROPERTY_PAIRS:
                for tail in (second + ' safe', second + '\n' + indent + 'safe',
                             '# comment\n\n' + indent + second + ' [safe]',
                             second + ' {name: safe}', second + ' |2\n' + indent + '  text'):
                    self.assert_invalid_parent(owner + first + '\n' + indent + tail + '\nfocus: content')

    def test_duplicates_after_empty_parent_and_multiple_property_rows_fail(self):
        for first, second in self.PROPERTY_PAIRS:
            other = '!!str' if first.startswith('&') else '&one'
            for owner, indent in self.OWNERS[:4]:
                declaration = owner + '\n' + indent + first + '\n' + indent + other + '\n' + indent + second + ' safe\nfocus: content'
                self.assert_invalid_parent(declaration)

    def test_duplicate_properties_reach_all_cli_gates(self):
        declarations = (
            'title: &one\n  &two safe',
            'title: !!str\n  !local\n  safe',
            'authors:\n  - &one\n    &two [safe]',
            'authors:\n  - title: &one\n      &two {name: safe}',
            'metadata:\n  title: !local\n    &one\n    !!str |2\n      text',
            'authors:\n  - &mapping title: &one\n      &two safe',
        )
        for declaration in declarations:
            for check in ('focus','structure','process','sources','citations','all'):
                with self.subTest(declaration=declaration, check=check):
                    result = self.cli(declaration + '\nfocus: content', check)
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn('official (9/10)', result.stdout)

    def test_valid_split_anchor_and_tag_properties_preserve_node_identity(self):
        for owner, indent in self.OWNERS:
            for first, second in (('&one', '!!str'), ('!!str', '&one')):
                for tail in ('safe', '[safe]', '{name: safe}', '|2\n' + indent + '  text'):
                    declaration = owner + first + '\n' + indent + second + ' ' + tail + '\nfocus: none'
                    with self.subTest(declaration=declaration):
                        metadata = vr.validated_metadata(self.report(declaration))
                        self.assertIsNone(vr.metadata_problem(metadata))
                        self.assertEqual(metadata['focus'], [])
                        self.assertEqual(self.cli(declaration, 'all').returncode, 0)
        for declaration in ('title:\n    &one\n  !!str\n  safe',
                            'title: &one\n  # comment\n\n    !!str\n  |2\n  text'):
            with self.subTest(declaration=declaration):
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration + '\nfocus: none'))))
                self.assertEqual(self.cli(declaration + '\nfocus: none', 'all').returncode, 0)

    def test_property_state_expires_for_distinct_nodes_siblings_and_items(self):
        declarations = (
            'title: &one safe\nother: &two safe',
            'title: &one\nother: &two safe',
            'title:\n  &one\n  safe\nother:\n  &two\n  safe',
            'metadata: &one\n  title: &two safe\n  other: &three safe',
            'metadata:\n  title: &one\n    safe\n  other: &two\n    safe',
            'authors: &one\n  - &two\n    safe\n  - &three safe',
            'authors:\n- &one\n  safe\n- &two safe',
            'authors:\n  - &one title: &two\n      safe\n    other: &three safe',
            'authors:\n  - &one\n    title: &two safe\n  - &three\n    title: &four safe',
            'metadata: &one\n  !!map\n  child: &two\n    !!str\n    safe',
            'metadata: &one\n  {name: &two safe, other: &three safe}',
            'metadata: &one\n  [&two safe, &three safe]',
            'title: &one |\n  &two\n  !!str\n  !local\nother: &three safe',
        )
        for declaration in declarations:
            with self.subTest(declaration=declaration):
                report = self.report(declaration + '\nfocus: none')
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(report)))
                self.assertEqual(vr.declared_focus(report), [])
                self.assertEqual(self.cli(declaration + '\nfocus: none', 'all').returncode, 0)


class Final203ValidPlainAndQuotedScalars(unittest.TestCase):
    report = Final184Test.report
    cli = Final184Test.cli
    VALID = ('title: -,5', 'title: -]', 'title: -}', 'metadata:\n  title: -,5',
             'authors:\n  - "a\\": b"', 'authors:\n  - "x \\": y \\" z"',
             'metadata:\n  note: "a\\": b"')

    def test_valid_block_scalars_are_not_refused(self):
        for declaration in self.VALID:
            declaration += '\nfocus: none'
            with self.subTest(declaration=declaration):
                self.assertIsNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration))))
                self.assertEqual(self.cli(declaration, 'all').returncode, 0)

    def test_complete_escaped_keys_still_refused(self):
        for declaration in ('"a\\"b": safe', 'metadata:\n  "a\\"b": safe', 'authors:\n  - "a\\"b": safe'):
            with self.subTest(declaration=declaration):
                self.assertIsNotNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration + '\nfocus: none'))))

    def test_dash_before_flow_delimiter_still_refused_inside_flow(self):
        for declaration in ('metadata: {note: [-, x]}', 'metadata: [-]', 'metadata: {a: -}'):
            with self.subTest(declaration=declaration):
                self.assertIsNotNone(vr.metadata_problem(vr.validated_metadata(self.report(declaration + '\nfocus: none'))))


if __name__ == "__main__":
    unittest.main()
