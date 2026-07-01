"""
Tests for the hoare-agent Python SDK.

Run with:
    cd sdk/python
    pytest tests/ -v
"""

from __future__ import annotations

import pytest

from hoareagent import verify, verified, HoareResult


# ---------------------------------------------------------------------------
# HoareResult tests
# ---------------------------------------------------------------------------

class TestHoareResult:
    def test_bool_true_when_verified(self):
        r = HoareResult(verified=True, verdict="VERIFIED")
        assert bool(r) is True

    def test_bool_false_when_not_verified(self):
        r = HoareResult(verified=False, verdict="COUNTEREXAMPLE")
        assert bool(r) is False

    def test_str_contains_verdict(self):
        r = HoareResult(verified=True, verdict="VERIFIED")
        assert "VERIFIED" in str(r)

    def test_str_includes_counterexample(self):
        r = HoareResult(verified=False, verdict="COUNTEREXAMPLE", counterexample="x = 0")
        assert "x = 0" in str(r)

    def test_repr_roundtrip(self):
        r = HoareResult(verified=True, verdict="VERIFIED", elapsed_ms=12)
        assert "VERIFIED" in repr(r)
        assert "12ms" in repr(r)


# ---------------------------------------------------------------------------
# verify() tests
# ---------------------------------------------------------------------------

class TestVerify:
    def test_trivially_true(self):
        r = verify("", pre="True", post="True")
        assert r.verified
        assert r.verdict == "VERIFIED"

    def test_implied_condition_verifies(self):
        # n > 5 implies n > 0
        r = verify("", pre="n > 5", post="n > 0")
        assert r.verified

    def test_false_condition_produces_counterexample(self):
        r = verify("", pre="n >= 0", post="n > 100")
        assert not r.verified
        assert r.verdict == "COUNTEREXAMPLE"
        assert r.counterexample != ""

    def test_multi_variable(self):
        r = verify("", pre="x >= 0 and y >= 0", post="x >= 0")
        assert r.verified

    def test_elapsed_ms_populated(self):
        r = verify("", pre="n >= 0", post="n >= 0")
        assert r.elapsed_ms >= 0

    def test_callable_input_with_docstring(self):
        def add(x, y):
            """
            :pre:  x >= 0 and y >= 0
            :post: x >= 0
            """
            return x + y

        r = verify(code=add)
        assert r.verified

    def test_callable_explicit_conditions_override_docstring(self):
        def add(x, y):
            """
            :pre:  x >= 0
            :post: x > 100   # this would fail
            """
            return x + y

        # Explicit conditions override docstring
        r = verify(code=add, pre="x >= 0", post="x >= 0")
        assert r.verified

    def test_source_string_with_comment_annotations(self):
        source = "# pre: n > 5\n# post: n > 0\ndef fn(n): return n"
        r = verify(source)
        assert r.verified

    def test_default_conditions_trivially_verify(self):
        def no_annotations(x):
            return x

        r = verify(code=no_annotations)
        assert r.verified  # True/True always verifies

    def test_smt2_pre_condition(self):
        r = verify("", pre="(> n 5)", post="n > 0")
        assert r.verified

    def test_loop_invariants(self):
        r = verify(
            "",
            pre="n >= 0",
            post="n >= 0",
            loop_invariants=["n >= 0"],
        )
        assert r.verified

    def test_error_result_on_bad_expression(self):
        r = verify("", pre="not a valid expression !!!", post="True")
        assert not r.verified
        assert r.verdict == "ERROR"
        assert r.error_detail != ""


# ---------------------------------------------------------------------------
# @verified decorator tests
# ---------------------------------------------------------------------------

class TestVerifiedDecorator:
    def test_verified_function_is_callable(self):
        @verified(pre="x >= 0", post="x >= 0")
        def identity(x):
            return x

        assert identity(5) == 5

    def test_hoare_result_attached(self):
        @verified(pre="x >= 0", post="x >= 0")
        def identity(x):
            return x

        assert hasattr(identity, "hoare_result")
        assert identity.hoare_result.verified

    def test_failed_verification_stored(self):
        @verified(pre="x >= 0", post="x > 100")
        def identity(x):
            return x

        assert not identity.hoare_result.verified

    def test_raise_on_failure(self):
        with pytest.raises(AssertionError, match="Hoare verification failed"):
            @verified(pre="x >= 0", post="x > 100", raise_on_failure=True)
            def bad(x):
                return x

    def test_wraps_preserves_name(self):
        @verified(pre="True", post="True")
        def my_named_fn():
            pass

        assert my_named_fn.__name__ == "my_named_fn"

    def test_hoare_pre_post_attached(self):
        @verified(pre="n >= 0", post="n >= 0")
        def fn(n):
            return n

        assert fn.hoare_pre == "n >= 0"
        assert fn.hoare_post == "n >= 0"


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLI:
    def test_cli_help(self):
        from hoareagent.cli import main
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_cli_verify_inline_passes(self, tmp_path):
        from hoareagent.cli import main
        with pytest.raises(SystemExit) as exc_info:
            main(["verify", "--pre", "x >= 0", "--post", "x >= 0"])
        assert exc_info.value.code == 0

    def test_cli_verify_file(self, tmp_path):
        from hoareagent.cli import main
        f = tmp_path / "sample.py"
        f.write_text(
            'def add(x, y):\n'
            '    """\n'
            '    :pre:  x >= 0 and y >= 0\n'
            '    :post: x >= 0\n'
            '    """\n'
            '    return x + y\n'
        )
        with pytest.raises(SystemExit) as exc_info:
            main(["verify", str(f)])
        assert exc_info.value.code == 0

    def test_cli_verify_file_with_failing_triple(self, tmp_path):
        from hoareagent.cli import main
        f = tmp_path / "bad.py"
        f.write_text(
            'def bad(x):\n'
            '    """\n'
            '    :pre:  x >= 0\n'
            '    :post: x > 100\n'
            '    """\n'
            '    return x\n'
        )
        with pytest.raises(SystemExit) as exc_info:
            main(["verify", str(f)])
        assert exc_info.value.code == 1
