"""
CodeManager — shared utilities for parsing and validating LLM-generated code.

Previously _parse_code_blocks() was defined in coder.py and imported by verifier.py
across module boundaries. Moving it here gives a single seam for all code-generation
and code-fixing agents (CoderAgent, VerifierAgent, and any future agents).

Public surface
--------------
parse_code_blocks(text)     — extract {filepath: content} from LLM output
strip_markdown_fences(text) — remove leading/trailing ``` fences from a code block
validate_syntax(files)      — compile-check all .py files, return list[str] of errors
"""
from __future__ import annotations

import ast
import re


def parse_code_blocks(text: str) -> dict[str, str]:
    """Parse LLM output for file blocks in the canonical format:

        === FILE: path/to/file.py ===
        <content>

    Returns a mapping of relative path → file content, with markdown fences and
    trailing LLM explanation text stripped.
    """
    files: dict[str, str] = {}
    pattern = re.compile(r"===\s*FILE:\s*(.+?)\s*===\n(.*?)(?====\s*FILE:|\Z)", re.DOTALL)
    for match in pattern.finditer(text):
        rel_path = match.group(1).strip()
        content = match.group(2).strip()
        content = strip_markdown_fences(content)
        # Truncate at common LLM explanation markers
        clean_lines = []
        for line in content.split("\n"):
            if re.match(
                r"^(FIX:|EXPLANATION:|NOTE:|CHANGES?:|This (?:fix|change|update|removes?|adds?))",
                line.strip(),
            ):
                break
            clean_lines.append(line)
        files[rel_path] = "\n".join(clean_lines).rstrip()
    return files


def strip_markdown_fences(text: str) -> str:
    """Remove leading ```lang and trailing ``` fences from a code block."""
    text = re.sub(r"^```\w*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text


def validate_syntax(files: dict[str, str]) -> list[str]:
    """Compile-check every .py file in *files*.

    Returns a list of error strings (empty = all OK).
    """
    errors: list[str] = []
    for path, content in files.items():
        if not path.endswith(".py"):
            continue
        try:
            ast.parse(content)
        except SyntaxError as e:
            errors.append(f"{path}: SyntaxError at line {e.lineno}: {e.msg}")
    return errors
