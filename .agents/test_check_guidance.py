"""Negative controls for the model-free agent guidance checker."""
from pathlib import Path
import tempfile
import unittest

from check_guidance import DOCS, REQUIRED, validate


class GuidanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for relative in DOCS:
            self.write(relative, "# Guidance\n")
        for name in sorted(REQUIRED):
            self.write(f".agents/skills/{name}/SKILL.md",
                       f"---\nname: {name}\ndescription: A reusable skill.\n---\n# Instructions\n")
        self.index = "".join(f"- [{n}](.agents/skills/{n}/SKILL.md): Skill.\n"
                             for n in sorted(REQUIRED))
        self.write("AGENTS.md", self.index)

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_valid(self):
        self.assertEqual(validate(self.root), [])

    def test_missing_required_skill(self):
        path = self.root / ".agents/skills/tinybuilder-onboard/SKILL.md"
        path.unlink()
        path.parent.rmdir()
        self.assertTrue(any("required skill missing" in e for e in validate(self.root)))

    def test_malformed_frontmatter(self):
        self.write(".agents/skills/tinybuilder-onboard/SKILL.md", "# No metadata\n")
        self.assertTrue(any("frontmatter" in e for e in validate(self.root)))

    def test_duplicate_name_and_invalid_description(self):
        self.write(".agents/skills/tinybuilder-onboard/SKILL.md",
                   "---\nname: tinybuilder-release\ndescription: \n---\n# Body\n")
        errors = validate(self.root)
        self.assertTrue(any("directory mismatch" in e for e in errors))
        self.assertTrue(any("duplicate skill name" in e for e in errors))
        self.assertTrue(any("invalid single-line description" in e for e in errors))

    def test_index_coverage_and_uniqueness(self):
        lines = self.index.splitlines(keepends=True)
        self.write("AGENTS.md", "".join(lines[1:]) + lines[-1])
        errors = validate(self.root)
        self.assertTrue(any("duplicate skill index" in e for e in errors))
        self.assertTrue(any("skill not indexed" in e for e in errors))

    def test_local_links_and_fenced_examples(self):
        self.write("docs/AGENT_GUIDE.md",
                   "[existing](../AGENTS.md)\n[external](https://example.com/)\n"
                   "\x60\x60\x60\n[example](absent.md)\n\x60\x60\x60\n")
        self.assertEqual(validate(self.root), [])
        self.write("docs/AGENT_GUIDE.md", "[broken](absent.md)\n[escape](../../outside.md)\n")
        self.assertEqual(sum("invalid relative link" in e for e in validate(self.root)), 2)


if __name__ == "__main__":
    unittest.main()
