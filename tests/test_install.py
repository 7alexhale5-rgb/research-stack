"""install.sh into a temp HOME: ships the skill, leaves machine-owned files alone.
Run: python3 -m unittest discover tests"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class InstallTest(unittest.TestCase):
    def test_install_preserves_local_evals_and_config(self):
        with tempfile.TemporaryDirectory() as home:
            skill = Path(home, ".claude/skills/research-stack")
            owned = {
                "local/OVERLAY.md": "private add-on\n",
                "evals/regression-history.jsonl": "{}\n",
                "config/config.md": "CACHE_DIR=/somewhere\n",
            }
            for rel, body in owned.items():
                (skill / rel).parent.mkdir(parents=True, exist_ok=True)
                (skill / rel).write_text(body, encoding="utf-8")
            stale = skill / "references/old-private-notes.md"
            stale.parent.mkdir(parents=True, exist_ok=True)
            stale.write_text("old\n", encoding="utf-8")

            env = dict(os.environ, HOME=home)
            r = subprocess.run(["bash", str(ROOT / "install.sh")], cwd=tempfile.gettempdir(),
                               env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

            for rel, body in owned.items():
                self.assertEqual((skill / rel).read_text(encoding="utf-8"), body, rel)
            self.assertTrue(stale.exists(), "install must never delete")
            self.assertIn("references/old-private-notes.md", r.stdout)
            for rel in ["SKILL.md", "focus/seo.md", "references/tool-registry.json", "scripts/gather.py"]:
                self.assertTrue((skill / rel).exists(), rel)
            cmd = Path(home, ".claude/commands/research-stack.md").read_text(encoding="utf-8")
            self.assertTrue(cmd.startswith("---\ndescription:"), "command keeps its front matter")


if __name__ == "__main__":
    unittest.main()
