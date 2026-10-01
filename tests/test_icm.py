"""ICM layout checks: the router, the system map and every room contract stay in step.
Run: python3 -m unittest discover tests"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROOM_SECTIONS = ["## Inputs", "## Process", "## Outputs", "## Human check"]
MAP_SECTIONS = ["## Purpose and boundary", "## Start or resume work",
                "## Stable rules and changing work", "## Status and first check"]
LINK_RE = re.compile(r"\]\(([^)#\s]+/CONTEXT\.md)\)")


def router_rooms():
    text = (ROOT / "CLAUDE.md").read_text()
    return sorted(set(LINK_RE.findall(text)))


class IcmLayoutTest(unittest.TestCase):
    def test_agents_md_is_the_router(self):
        agents = ROOT / "AGENTS.md"
        self.assertTrue(agents.exists())
        self.assertEqual(agents.read_text(), (ROOT / "CLAUDE.md").read_text())

    def test_router_names_icm_and_rooms_exist(self):
        text = (ROOT / "CLAUDE.md").read_text()
        self.assertIn("This repo follows ICM", text)
        rooms = router_rooms()
        self.assertTrue(rooms)
        for rel in rooms:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_every_room_contract_has_the_four_sections(self):
        for rel in router_rooms():
            text = (ROOT / rel).read_text()
            for heading in ROOM_SECTIONS:
                self.assertIn(heading, text, f"{rel}: {heading}")

    def test_system_map_lists_exactly_the_router_rooms(self):
        text = (ROOT / "CONTEXT.md").read_text()
        for heading in MAP_SECTIONS:
            self.assertIn(heading, text)
        self.assertEqual(sorted(set(LINK_RE.findall(text))), router_rooms())

    def test_every_top_level_folder_is_a_room_or_declared(self):
        declared = {Path(r).parts[0] for r in router_rooms()}
        ignored = {".git"}
        for p in ROOT.iterdir():
            if p.is_dir() and p.name not in ignored and not p.name.startswith("__"):
                self.assertIn(p.name, declared, f"{p.name}/ has no room contract in the router")


if __name__ == "__main__":
    unittest.main()
