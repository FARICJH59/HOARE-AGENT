"""
Unit tests for the hoare-agent Python SDK.

Run with:
    cd sdk/python
    pip install -e ".[dev]"
    pytest tests/ -v
"""

from __future__ import annotations

import json
import sys
import os
from pathlib import Path

import pytest

# Ensure sdk/python is on the path when run directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hoare_agent import verify, VerificationVerdict
from hoare_agent._models import HoareTriple, VerificationResult
from hoare_agent._verifier import run_z3
from hoare_agent._parser import parse_file


# ─────────────────────────────────────────────────────────────────────────────
# verify() public API
# ─────────────────────────────────────────────────────────────────────────────

class TestVerifyAPI:
    def test_valid_triple_returns_verified(self):
        result = verify(precondition="n >= 0", postcondition="n >= 0")
        assert result.verified
        assert result.verdict == VerificationVerdict.VERIFIED

    def test_verified_result_is_truthy(self):
        result = verify(precondition="n >= 0", postcondition="n >= 0")
        assert bool(result) is True

    def test_counterexample_triple_fails(self):
        result = verify(precondition="n >= 0", postcondition="n > 100")
        assert not result.verified
        assert result.verdict == VerificationVerdict.COUNTEREXAMPLE

    def test_counterexample_result_is_falsy(self):
        result = verify(precondition="n >= 0", postcondition="n > 100")
        assert bool(result) is False

    def test_implication_verifies(self):
        result = verify(precondition="n > 10", postcondition="n >= 0")
        assert result.verified

    def test_loop_invariant_accepted(self):
        result = verify(
            precondition="n >= 0 and i == 0",
            postcondition="n >= 0",
            loop_invariants=["i >= 0"],
        )
        assert result.verified

    def test_program_text_accepted(self):
        result = verify(
            precondition="n >= 0",
            postcondition="n >= 0",
            program="def transform(data): return data",
        )
        assert result.verified

    def test_elapsed_ms_is_non_negative(self):
        result = verify(precondition="n >= 0", postcondition="n >= 0")
        assert result.elapsed_ms >= 0

    def test_str_representation_verified(self):
        result = verify(precondition="n >= 0", postcondition="n >= 0")
        assert "VERIFIED" in str(result)

    def test_str_representation_counterexample(self):
        result = verify(precondition="n >= 0", postcondition="n > 100")
        assert "COUNTEREXAMPLE" in str(result)

    def test_multi_variable_triple_verifies(self):
        result = verify(precondition="x > 0 and y > 0", postcondition="x > 0")
        assert result.verified


# ─────────────────────────────────────────────────────────────────────────────
# HoareTriple model
# ─────────────────────────────────────────────────────────────────────────────

class TestHoareTripleModel:
    def test_default_loop_invariants_is_empty(self):
        t = HoareTriple(precondition="n >= 0", postcondition="n >= 0")
        assert t.loop_invariants == []

    def test_default_program_is_empty(self):
        t = HoareTriple(precondition="n >= 0", postcondition="n >= 0")
        assert t.program == ""


# ─────────────────────────────────────────────────────────────────────────────
# File annotation parser
# ─────────────────────────────────────────────────────────────────────────────

class TestParser:
    def _write(self, tmp_path: Path, filename: str, content: str) -> Path:
        p = tmp_path / filename
        p.write_text(content, encoding="utf-8")
        return p

    def test_parses_pre_post_annotations(self, tmp_path):
        src = "# @pre: n >= 0\n# @post: n >= 0\ndef f(): pass\n"
        path = self._write(tmp_path, "f.py", src)
        triple = parse_file(path)
        assert triple is not None
        assert triple.precondition == "n >= 0"
        assert triple.postcondition == "n >= 0"

    def test_parses_inv_annotation(self, tmp_path):
        src = "# @pre: n >= 0\n# @post: n >= 0\n# @inv: i >= 0\ndef f(): pass\n"
        path = self._write(tmp_path, "f.py", src)
        triple = parse_file(path)
        assert triple is not None
        assert triple.loop_invariants == ["i >= 0"]

    def test_returns_none_when_no_annotations(self, tmp_path):
        src = "def f(): pass\n"
        path = self._write(tmp_path, "f.py", src)
        assert parse_file(path) is None

    def test_raises_when_pre_without_post(self, tmp_path):
        src = "# @pre: n >= 0\ndef f(): pass\n"
        path = self._write(tmp_path, "f.py", src)
        with pytest.raises(ValueError, match="@post"):
            parse_file(path)

    def test_raises_when_post_without_pre(self, tmp_path):
        src = "# @post: n >= 0\ndef f(): pass\n"
        path = self._write(tmp_path, "f.py", src)
        with pytest.raises(ValueError, match="@pre"):
            parse_file(path)

    def test_parses_json_triple(self, tmp_path):
        data = {
            "precondition":  "n >= 0",
            "program":       "def f(): pass",
            "postcondition": "n >= 0",
            "loop_invariants": ["i >= 0"],
        }
        path = self._write(tmp_path, "triple.json", json.dumps(data))
        triple = parse_file(path)
        assert triple is not None
        assert triple.precondition == "n >= 0"
        assert triple.loop_invariants == ["i >= 0"]

    def test_case_insensitive_annotations(self, tmp_path):
        src = "# @PRE: x > 0\n# @POST: x > 0\ndef f(): pass\n"
        path = self._write(tmp_path, "f.py", src)
        triple = parse_file(path)
        assert triple is not None
        assert triple.precondition == "x > 0"


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

class TestCLI:
    def _write(self, tmp_path: Path, filename: str, content: str) -> Path:
        p = tmp_path / filename
        p.write_text(content, encoding="utf-8")
        return p

    def _run(self, argv: list) -> int:
        from hoare_agent.cli import main
        with pytest.raises(SystemExit) as exc_info:
            main(argv)
        return exc_info.value.code

    def test_verify_annotated_file_succeeds(self, tmp_path):
        src = "# @pre: n >= 0\n# @post: n >= 0\ndef f(): pass\n"
        path = self._write(tmp_path, "ok.py", src)
        code = self._run(["verify", str(path)])
        assert code == 0

    def test_verify_with_flags_succeeds(self, tmp_path):
        src = "def f(): pass\n"
        path = self._write(tmp_path, "f.py", src)
        code = self._run(["verify", "--pre", "n >= 0", "--post", "n >= 0", str(path)])
        assert code == 0

    def test_verify_counterexample_exits_2(self, tmp_path):
        src = "# @pre: n >= 0\n# @post: n > 100\ndef f(): pass\n"
        path = self._write(tmp_path, "bad.py", src)
        code = self._run(["verify", str(path)])
        assert code == 2

    def test_verify_missing_file_exits_1(self, tmp_path):
        code = self._run(["verify", str(tmp_path / "nonexistent.py")])
        assert code == 1

    def test_verify_no_annotations_exits_1(self, tmp_path):
        src = "def f(): pass\n"
        path = self._write(tmp_path, "f.py", src)
        code = self._run(["verify", str(path)])
        assert code == 1

    def test_verify_json_triple_file(self, tmp_path):
        data = {
            "precondition":  "n >= 0",
            "postcondition": "n >= 0",
        }
        path = self._write(tmp_path, "t.json", json.dumps(data))
        code = self._run(["verify", str(path)])
        assert code == 0

    def test_verify_json_output(self, tmp_path, capsys):
        src = "# @pre: n >= 0\n# @post: n >= 0\ndef f(): pass\n"
        path = self._write(tmp_path, "ok.py", src)
        code = self._run(["verify", "--json", str(path)])
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["verified"] is True
        assert code == 0

    def test_verify_pre_without_post_flag_exits_1(self, tmp_path):
        src = "def f(): pass\n"
        path = self._write(tmp_path, "f.py", src)
        code = self._run(["verify", "--pre", "n >= 0", str(path)])
        assert code == 1
