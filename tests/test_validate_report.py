"""Tests for research-stack validate_report. Run: python3 -m unittest discover tests"""

import io
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import validate_report as vr  # noqa: E402

FILLER = " ".join(["word"] * 200)

GOOD = f"""# Research: fixture (good)

## Decision answer
- Use the keyless API; it needs no setup [HN:91][WS].

## Sub-question answers
**Q1: Does the API need a key?**
- No key needed as of 2026-09 [PX + FC:docs.example.com].

## Contradictions
- Source A ranks by points, source B by date [PX][WS].

## Patterns
- Compress before hand-off appears in 2+ sources [PX + FC:example.org].

## Coverage gaps
- none

{FILLER}

- https://arxiv.org/abs/2506.18096
- https://docs.python.org/3/library/urllib.html
- https://github.com/example/repo
"""

BAD = """# Fixture: bad report

Some findings with no tags or structure. A dead link:
https://this-domain-does-not-exist.invalid/article and a weak one
https://random-unknown-blog.biz/post.
"""


class StructureTest(unittest.TestCase):
    def test_each_mandatory_element_fails_when_missing(self):
        for aliases, _ in vr.SECTIONS:
            self.assertEqual(vr.check_structure(GOOD.replace('## ' + aliases[0], 'ordinary text'))[0], 'FAIL')
        self.assertEqual(vr.check_structure(vr.BRACKET_RE.sub('', GOOD))[0], 'FAIL')

    def test_good_report_passes(self):
        status, lines = vr.check_structure(GOOD)
        self.assertEqual(status, "PASS", lines)

    def test_bad_report_fails(self):
        status, lines = vr.check_structure(BAD)
        self.assertEqual(status, "FAIL", lines)

    def test_section_word_in_body_does_not_count(self):
        text = "No contradictions or patterns here, and no gaps. [WS][HN:1]\n" + FILLER
        status, lines = vr.check_structure(text)
        self.assertEqual(status, "FAIL", lines)

    def test_combined_tags_are_counted(self):
        tags = vr.extract_tags("claim [PX + FC:docs.example.com] and [HN:42]")
        self.assertEqual(tags, ["PX", "FC", "HN"])

    def test_non_tag_brackets_are_ignored(self):
        self.assertEqual(vr.extract_tags("see [the docs] and [1]"), [])

    def test_single_type_warns(self):
        text = GOOD.replace("[HN:91]", "[WS]").replace("PX", "WS").replace("FC:", "WS:")
        status, lines = vr.check_structure(text)
        self.assertIn("only 1 source type", "\n".join(lines))
        self.assertIn(status, ("PASS", "WARN"))


class SourcesTest(unittest.TestCase):
    def test_misleading_authority_does_not_gain_trust(self):
        for url in ['https://untrusted.example/arxiv.org/article', 'https://arxiv.org.untrusted.example/article', 'https://arxiv.org@untrusted.example/article']:
            self.assertEqual(vr.classify_url(url), 'unknown')
        self.assertEqual(vr.classify_url('https://export.arxiv.org/article'), 'academic')

    def test_ipv6_extraction_and_malformed_url(self):
        url = 'https://[2606:4700:4700::1111]/'
        self.assertEqual(vr.extract_urls('see [' + url + ']'), [url])
        self.assertEqual(vr.classify_url('https://[invalid'), 'unknown')
        status, lines = vr.check_sources(url)
        self.assertEqual(status, 'WARN')
        self.assertIn('unknown (4/10): 1 source', '\n'.join(lines))

    def test_classify(self):
        self.assertEqual(vr.classify_url("https://arxiv.org/abs/1"), "academic")
        self.assertEqual(vr.classify_url("https://www.reddit.com/r/x"), "community")
        self.assertEqual(vr.classify_url("https://agency.gov/rule"), "official")
        self.assertEqual(vr.classify_url("https://random.biz/p"), "unknown")

    def test_good_sources_pass(self):
        status, _ = vr.check_sources(GOOD)
        self.assertEqual(status, "PASS")

    def test_informal_sources_warn(self):
        status, lines = vr.check_sources(BAD)
        self.assertEqual(status, "WARN")
        self.assertIn("mostly informal", "\n".join(lines))

    def test_trailing_punctuation_is_stripped(self):
        self.assertEqual(vr.extract_urls("see https://a.org/x."), ["https://a.org/x"])


def fake_fetch(table):
    def fetch(url, method, timeout):
        result = table[(url, method)] if (url, method) in table else table[url]
        if isinstance(result, Exception):
            raise result
        if result >= 400:
            raise urllib.error.HTTPError(url, result, "x", {}, None)
        return result

    return fetch


class SsrfGuardTest(unittest.TestCase):
    """CRITICAL: the citation fetcher must never touch loopback/private/link-local/
    reserved addresses, and must never follow a redirect into one either."""

    def test_shared_address_space_is_rejected(self):
        for host in ['100.64.0.1', '100.127.255.254']:
            with self.assertRaises(ValueError):
                vr._reject_unsafe_url('http://' + host + '/')

    def test_proxy_handler_is_disabled(self):
        handlers = [h for h in vr._SAFE_OPENER.handlers if isinstance(h, vr.urllib.request.ProxyHandler)]
        self.assertTrue(all(not h.proxies for h in handlers))

    def test_loopback_ipv4_is_rejected(self):
        with self.assertRaises(ValueError):
            vr._reject_unsafe_url("http://127.0.0.1/admin")

    def test_ipv6_loopback_is_rejected(self):
        with self.assertRaises(ValueError):
            vr._reject_unsafe_url("http://[::1]/admin")

    def test_cloud_metadata_link_local_is_rejected(self):
        with self.assertRaises(ValueError):
            vr._reject_unsafe_url("http://169.254.169.254/latest/meta-data/")

    def test_private_ranges_are_rejected(self):
        for host in ("10.0.0.5", "172.16.0.5", "192.168.1.1"):
            with self.assertRaises(ValueError, msg=host):
                vr._reject_unsafe_url(f"http://{host}/x")

    def test_non_http_scheme_is_rejected(self):
        with self.assertRaises(ValueError):
            vr._reject_unsafe_url("file:///etc/passwd")
        with self.assertRaises(ValueError):
            vr._reject_unsafe_url("ftp://example.com/x")

    def test_public_ip_is_allowed(self):
        vr._reject_unsafe_url("http://93.184.216.34/x")  # does not raise

    def test_default_fetch_never_opens_a_socket_for_a_blocked_url(self):
        # the guard must fire before urlopen is even attempted; patch urlopen
        # to explode if reached, proving the block happens first.
        def boom(*a, **k):
            raise AssertionError("urlopen must not be called for a blocked URL")

        orig = vr.urllib.request.urlopen
        vr.urllib.request.urlopen = boom
        try:
            with self.assertRaises(ValueError):
                vr._default_fetch("http://127.0.0.1/admin", "HEAD", 5)
        finally:
            vr.urllib.request.urlopen = orig

    def test_classify_citation_reports_a_blocked_url_as_dead(self):
        kind, detail = vr.classify_citation("http://127.0.0.1/admin", vr._default_fetch)
        self.assertEqual(kind, "dead")
        self.assertIn("BLOCKED", detail)

    def test_classify_citation_blocks_cloud_metadata_too(self):
        kind, detail = vr.classify_citation(
            "http://169.254.169.254/latest/meta-data/", vr._default_fetch
        )
        self.assertEqual(kind, "dead")
        self.assertIn("BLOCKED", detail)

    def test_redirect_to_a_private_address_is_refused(self):
        class FakeResp:
            status = 302

        class RedirectingOpener:
            def open(self, req, timeout=None):
                # simulate the redirect handler being asked to follow a hop
                # into a private address, as urllib would on a 30x response
                vr._SafeRedirectHandler.redirect_request(
                    vr._SafeRedirectHandler(),
                    req,
                    None,
                    302,
                    "Found",
                    {},
                    "http://10.0.0.5/internal",
                )
                return FakeResp()  # pragma: no cover - unreachable if guard fires

        orig = vr._SAFE_OPENER
        vr._SAFE_OPENER = RedirectingOpener()
        try:
            with self.assertRaises(ValueError):
                vr._default_fetch("https://public.example.com/", "HEAD", 5)
        finally:
            vr._SAFE_OPENER = orig


class DnsRebindingTest(unittest.TestCase):
    """R2-4: the guard's own resolution must be the one actually connected to.
    Before the fix, _reject_unsafe_url resolved once to check safety, then
    urllib performed a second, independent lookup when it connected -- a
    hostname that answers public first and private second (classic DNS
    rebinding) would pass the check and still be fetched."""

    def test_pinned_resolver_ignores_a_later_different_answer(self):
        host = "rebinder.example.test"
        calls = {"n": 0}

        def stub_resolver(h, *_a, **_kw):
            calls["n"] += 1
            self.assertEqual(h, host)
            # First lookup (the safety check) answers public. Any further,
            # separate lookup is the rebinding attacker's private answer.
            ip = "93.184.216.34" if calls["n"] == 1 else "169.254.169.254"
            return [(vr.socket.AF_INET, vr.socket.SOCK_STREAM, 6, "", (ip, 0))]

        orig = vr._real_getaddrinfo
        # _real_getaddrinfo must be back to normal before _dns_pinning's own
        # finally restores socket.getaddrinfo from it, or the swap leaks into
        # later tests.
        with vr._dns_pinning():
            vr._real_getaddrinfo = stub_resolver
            try:
                vr._reject_unsafe_url(f"http://{host}/x")
                # This simulates the connection's own DNS lookup at connect
                # time -- the exact moment a rebinding attack fires.
                infos = vr.socket.getaddrinfo(host, 80)
                got_ip = infos[0][4][0]
            finally:
                vr._real_getaddrinfo = orig

        self.assertEqual(
            got_ip,
            "93.184.216.34",
            "connect must reuse the vetted address, not perform a fresh lookup",
        )
        self.assertEqual(
            calls["n"], 1, "a pinned host must resolve exactly once per fetch"
        )

    def test_resolver_is_restored_after_the_fetch(self):
        orig = vr.socket.getaddrinfo
        with vr._dns_pinning():
            self.assertIsNot(vr.socket.getaddrinfo, orig)
        self.assertIs(vr.socket.getaddrinfo, orig)

    def test_mixed_case_host_hits_the_same_pin(self):
        """R3-1: a host pinned in one case must be recognised in another, or
        the case-different spelling misses the pin cache and falls back to
        an unchecked, un-pinned lookup at connect time."""
        calls = {"n": 0}

        def stub_resolver(h, *_a, **_kw):
            calls["n"] += 1
            return [
                (vr.socket.AF_INET, vr.socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))
            ]

        orig = vr._real_getaddrinfo
        with vr._dns_pinning():
            vr._real_getaddrinfo = stub_resolver
            try:
                vr._reject_unsafe_url("http://Example.Test/x")
                infos = vr.socket.getaddrinfo("EXAMPLE.TEST", 80)
                got_ip = infos[0][4][0]
            finally:
                vr._real_getaddrinfo = orig

        self.assertEqual(got_ip, "93.184.216.34")
        self.assertEqual(
            calls["n"],
            1,
            "the case-different spelling must reuse the pin, not re-resolve",
        )

    def test_idn_host_hits_the_same_pin(self):
        """R3-1: a Unicode host and its IDNA/punycode form are the same host
        and must share one pin."""
        calls = {"n": 0}

        def stub_resolver(h, *_a, **_kw):
            calls["n"] += 1
            return [
                (vr.socket.AF_INET, vr.socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))
            ]

        orig = vr._real_getaddrinfo
        with vr._dns_pinning():
            vr._real_getaddrinfo = stub_resolver
            try:
                vr._reject_unsafe_url("http://xn--jxalpdlp.example/x")
                infos = vr.socket.getaddrinfo("δοκιμή.example", 80)
                got_ip = infos[0][4][0]
            finally:
                vr._real_getaddrinfo = orig

        self.assertEqual(got_ip, "93.184.216.34")
        self.assertEqual(
            calls["n"],
            1,
            "the Unicode form must reuse the punycode pin, not re-resolve",
        )

    def test_unknown_host_at_connect_time_is_still_validated(self):
        """R3-1: a host _pinned_getaddrinfo has never seen pinned must be
        validated itself, never silently passed through to a raw, unchecked
        resolver -- a private answer must still be refused."""

        def stub_resolver(h, *_a, **_kw):
            return [
                (
                    vr.socket.AF_INET,
                    vr.socket.SOCK_STREAM,
                    6,
                    "",
                    ("169.254.169.254", 0),
                )
            ]

        orig = vr._real_getaddrinfo
        with vr._dns_pinning():
            vr._real_getaddrinfo = stub_resolver
            try:
                with self.assertRaises(ValueError):
                    vr.socket.getaddrinfo("never-pinned.example.test", 80)
            finally:
                vr._real_getaddrinfo = orig

    def test_default_fetch_pins_for_the_whole_call(self):
        """End-to-end: a real (loopback, refused) fetch still goes through the
        pinning context, and getaddrinfo is restored afterward either way."""
        orig = vr.socket.getaddrinfo
        with self.assertRaises(ValueError):
            vr._default_fetch("http://127.0.0.1/admin", "HEAD", 5)
        self.assertIs(vr.socket.getaddrinfo, orig)


class CitationTest(unittest.TestCase):
    def test_live(self):
        kind, _ = vr.classify_citation(
            "https://a.org", fake_fetch({"https://a.org": 200})
        )
        self.assertEqual(kind, "live")

    def test_404_is_dead(self):
        kind, _ = vr.classify_citation(
            "https://a.org", fake_fetch({"https://a.org": 404})
        )
        self.assertEqual(kind, "dead")

    def test_bot_wall_is_unverified_not_dead(self):
        for code in (401, 403, 429, 503):
            kind, _ = vr.classify_citation(
                "https://a.org", fake_fetch({"https://a.org": code})
            )
            self.assertEqual(kind, "unverified", code)

    def test_head_refused_falls_back_to_get(self):
        table = {("https://a.org", "HEAD"): 405, ("https://a.org", "GET"): 200}
        kind, _ = vr.classify_citation("https://a.org", fake_fetch(table))
        self.assertEqual(kind, "live")

    def test_dns_failure_is_dead(self):
        err = urllib.error.URLError(OSError("name not known"))
        kind, _ = vr.classify_citation(
            "https://a.invalid", fake_fetch({"https://a.invalid": err})
        )
        self.assertEqual(kind, "dead")

    def test_many_dead_fails(self):
        urls = [f"https://d{i}.invalid/" for i in range(6)]
        fetch = fake_fetch({u: 404 for u in urls})
        status, _ = vr.check_citations("\n".join(urls), fetch=fetch)
        self.assertEqual(status, "FAIL")


class FixtureFileTest(unittest.TestCase):
    """Regression check named in SKILL.md: run the validator on a
    known-good and a known-bad report file and confirm it passes one and fails the other."""

    FIXTURES = ROOT / "tests/fixtures"

    def test_good_fixture_file_passes_structure(self):
        path = self.FIXTURES / "research-report-good.md"
        out = io.StringIO()
        with redirect_stdout(out):
            code = vr.main(["structure", str(path)])
        self.assertEqual(code, 0, out.getvalue())

    def test_bad_fixture_file_fails_structure(self):
        path = self.FIXTURES / "research-report-bad.md"
        out = io.StringIO()
        with redirect_stdout(out):
            code = vr.main(["structure", str(path)])
        self.assertEqual(code, 1, out.getvalue())


class CliTest(unittest.TestCase):
    def run_cli(self, text, *args):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "r.md"
            path.write_text(text)
            before = path.read_text()
            out = io.StringIO()
            with redirect_stdout(out):
                code = vr.main([*args, str(path)])
            self.assertEqual(
                path.read_text(), before, "validator must not write the report"
            )
            return code, out.getvalue()

    def test_structure_exit_codes(self):
        self.assertEqual(self.run_cli(GOOD, "structure")[0], 0)
        self.assertEqual(self.run_cli(BAD, "structure")[0], 1)

    def test_all_offline(self):
        code, out = self.run_cli(GOOD, "all", "--offline")
        self.assertEqual(code, 0)
        self.assertIn("Verdict: PASS", out)
        self.assertNotIn("Citations:", out)

    def test_missing_file_is_usage_error(self):
        self.assertEqual(vr.main(["structure", "/nonexistent/report.md"]), 2)


if __name__ == "__main__":
    unittest.main()
