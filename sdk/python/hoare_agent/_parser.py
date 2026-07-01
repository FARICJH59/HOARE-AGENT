"""
File annotation parser for the hoare-agent CLI.

Supports extracting Hoare triple annotations from Python files.

Annotation format (comment-based, anywhere in the file):

    # @pre:  <precondition expression>
    # @post: <postcondition expression>
    # @inv:  <loop invariant expression>   (repeatable)

Or JSON triple file (.json):

    {
      "precondition":  "n >= 0",
      "program":       "def transform(data): ...",
      "postcondition": "n >= 0",
      "loop_invariants": []
    }
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from hoare_agent._models import HoareTriple


_PRE_RE  = re.compile(r"#\s*@pre:\s*(.+)", re.IGNORECASE)
_POST_RE = re.compile(r"#\s*@post:\s*(.+)", re.IGNORECASE)
_INV_RE  = re.compile(r"#\s*@inv:\s*(.+)",  re.IGNORECASE)


def parse_file(path: Path) -> Optional[HoareTriple]:
    """
    Parse a file and return a HoareTriple if annotations are found.

    Returns None if no annotations are found.
    Raises ValueError if annotations are incomplete (pre without post or vice versa).
    """
    suffix = path.suffix.lower()

    if suffix == ".json":
        return _parse_json_file(path)

    # Default: treat as Python source and scan for comment annotations
    source = path.read_text(encoding="utf-8")
    return _parse_python_source(source, str(path))


def _parse_json_file(path: Path) -> HoareTriple:
    data = json.loads(path.read_text(encoding="utf-8"))
    return HoareTriple(
        precondition=data.get("precondition", "True"),
        program=data.get("program", ""),
        postcondition=data.get("postcondition", "True"),
        loop_invariants=data.get("loop_invariants", []),
    )


def _parse_python_source(source: str, filename: str = "<file>") -> Optional[HoareTriple]:
    pre_matches  = _PRE_RE.findall(source)
    post_matches = _POST_RE.findall(source)
    inv_matches  = _INV_RE.findall(source)

    if not pre_matches and not post_matches:
        return None

    if not pre_matches:
        raise ValueError(
            f"{filename}: found @post annotation but no @pre annotation. "
            "Add '# @pre: <expression>' to the file."
        )
    if not post_matches:
        raise ValueError(
            f"{filename}: found @pre annotation but no @post annotation. "
            "Add '# @post: <expression>' to the file."
        )

    # Use the last annotation of each type (allows progressive refinement)
    pre  = pre_matches[-1].strip()
    post = post_matches[-1].strip()
    invs = [i.strip() for i in inv_matches]

    return HoareTriple(
        precondition=pre,
        program=source,
        postcondition=post,
        loop_invariants=invs,
    )
