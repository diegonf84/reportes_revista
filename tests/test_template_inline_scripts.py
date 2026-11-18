"""Guard against inline template scripts that break JavaScript parsing.

A single invalid token in an inline ``<script>`` block discards the whole
block at parse time. No listener is registered, every form falls back to a
native GET submit, and the page silently reloads without doing anything.
That is exactly what ``function AppAlerts.escapeHtml() {}`` does: a function
declaration name must be a plain identifier, never a member expression.

These tests parse every inline script of every template so that this class
of defect fails loudly instead of degrading the UI into a no-op.
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "app" / "templates"

INLINE_SCRIPT_PATTERN = re.compile(r"<script>(.*?)</script>", re.DOTALL)
JINJA_EXPRESSION_PATTERN = re.compile(r"\{\{.*?\}\}", re.DOTALL)
MEMBER_FUNCTION_DECLARATION_PATTERN = re.compile(r"\bfunction\s+[A-Za-z_$][\w$]*\s*\.")


def _inline_scripts() -> list[tuple[Path, str]]:
    """Return every inline script block of every template, with its owner."""
    scripts: list[tuple[Path, str]] = []
    for template in sorted(TEMPLATES_DIR.rglob("*.html")):
        source = template.read_text(encoding="utf-8")
        for block in INLINE_SCRIPT_PATTERN.findall(source):
            scripts.append((template, block))
    return scripts


class InlineScriptSyntaxTests(unittest.TestCase):
    def test_no_member_expression_function_declarations(self):
        """`function AppAlerts.escapeHtml() {}` is not valid JavaScript."""
        offenders = []
        for template, block in _inline_scripts():
            for match in MEMBER_FUNCTION_DECLARATION_PATTERN.finditer(block):
                offenders.append(f"{template.name}: {match.group(0).strip()}")

        self.assertEqual(
            [],
            offenders,
            "Inline scripts declare functions with a member expression name, "
            "which makes the whole script block fail to parse:\n"
            + "\n".join(offenders),
        )

    @unittest.skipUnless(shutil.which("node"), "node is required to parse JavaScript")
    def test_inline_scripts_parse_as_valid_javascript(self):
        """Every inline script must survive a real JavaScript parser."""
        failures = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            for index, (template, block) in enumerate(_inline_scripts()):
                script_path = Path(tmp_dir) / f"script_{index}.js"
                script_path.write_text(
                    JINJA_EXPRESSION_PATTERN.sub("null", block),
                    encoding="utf-8",
                )
                result = subprocess.run(
                    ["node", "--check", str(script_path)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    error_line = next(
                        (line for line in result.stderr.splitlines() if "Error" in line),
                        result.stderr.strip(),
                    )
                    failures.append(f"{template.name}: {error_line.strip()}")

        self.assertEqual(
            [],
            failures,
            "Inline scripts that do not parse disable the whole page:\n"
            + "\n".join(failures),
        )


if __name__ == "__main__":
    unittest.main()
