"""Tests for focus lenses: validator focus checks and focus_check.py. Run: python3 -m unittest discover tests"""

import io
import json
import os
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
        self.assertEqual(vr.classify_url("https://owasp.org/Top10/2025/"), "official")
        self.assertEqual(vr.classify_url("https://www.nngroup.com/articles/x/"), "official")
        self.assertEqual(vr.classify_url("https://owasp.org.evil.example/"), "unknown")


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
        self.assertEqual(vr.classify_url("https://developers.ringcentral.com/guide/voice"), "official")
        self.assertEqual(vr.classify_url("https://vercel.com/docs/tracing"), "official")

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


if __name__ == "__main__":
    unittest.main()
