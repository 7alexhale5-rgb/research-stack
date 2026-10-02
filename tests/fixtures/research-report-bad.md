# Fixture: known-bad research report

This fixture is deliberately missing the required sections (Decision answer, Contradictions,
Patterns, Coverage gaps), carries no source tags, and links a dead and a low-quality domain. It
must FAIL `validate_report.py structure`. Used by `tests/test_validate_report.py` and by the
research-stack regression check in `skills/research-stack/SKILL.md`.

Some findings with no tags or structure. A dead link:
https://this-domain-does-not-exist.invalid/article and a weak one
https://random-unknown-blog.biz/post.
