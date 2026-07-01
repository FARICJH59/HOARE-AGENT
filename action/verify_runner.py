#!/usr/bin/env python3
"""
verify_runner.py — invoked by the GitHub Action composite step.

Reads environment variables set by action.yml and runs hoare-agent verify
on each matched file, then writes GitHub Actions step outputs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ── Read inputs from environment ──────────────────────────────────────────
HA_PATH             = os.environ.get("HA_PATH", "**/*.py").strip()
HA_PRE              = os.environ.get("HA_PRE",  "").strip() or None
HA_POST             = os.environ.get("HA_POST", "").strip() or None
HA_TIMEOUT_MS       = int(os.environ.get("HA_TIMEOUT_MS", "5000"))
GITHUB_OUTPUT       = os.environ.get("GITHUB_OUTPUT", "")
GITHUB_STEP_SUMMARY = os.environ.get("GITHUB_STEP_SUMMARY", "")
WORKSPACE           = os.environ.get("GITHUB_WORKSPACE", ".")


# ── Helpers (defined before use) ──────────────────────────────────────────
def _write_output(name: str, value: str) -> None:
    if GITHUB_OUTPUT:
        with open(GITHUB_OUTPUT, "a") as fh:
            fh.write(f"{name}={value}\n")


def _append_summary(text: str) -> None:
    if GITHUB_STEP_SUMMARY:
        with open(GITHUB_STEP_SUMMARY, "a") as fh:
            fh.write(text + "\n")


# ── Collect files ─────────────────────────────────────────────────────────
workspace = Path(WORKSPACE)
patterns  = HA_PATH.split()
files: list[Path] = []

for pattern in patterns:
    # Exclude the action directory and SDK itself
    matched = [
        p for p in workspace.glob(pattern)
        if p.is_file()
        and "action/" not in str(p.relative_to(workspace))
        and "sdk/" not in str(p.relative_to(workspace))
        and not p.name.startswith(".")
    ]
    files.extend(matched)

files = sorted(set(files))

if not files:
    print(f"[hoare-agent] No Python files matched pattern(s): {HA_PATH}")
    _write_output("verified", "true")
    _write_output("summary", "No files matched.")
    sys.exit(0)


# ── Import SDK ────────────────────────────────────────────────────────────
try:
    from hoareagent._core import verify
    from hoareagent.cli import _extract_specs_from_source
except ImportError as exc:
    print(f"[hoare-agent] Failed to import SDK: {exc}", file=sys.stderr)
    sys.exit(1)


# ── Run verification ──────────────────────────────────────────────────────
total   = 0
passed  = 0
failed  = 0
summary_lines: list[str] = ["## HOARE-AGENT Verification Results\n"]
summary_lines.append("| File | Function | Pre | Post | Verdict | Elapsed |")
summary_lines.append("|------|----------|-----|------|---------|---------|")

for fpath in files:
    rel = fpath.relative_to(workspace)
    source = fpath.read_text(encoding="utf-8")

    if HA_PRE is not None or HA_POST is not None:
        # User supplied explicit conditions — apply to whole file
        result = verify(source, pre=HA_PRE, post=HA_POST, timeout_ms=HA_TIMEOUT_MS)
        total  += 1
        icon    = "\u2705" if result.verified else "\u274c"
        print(f"  {icon}  {rel}  [{result.verdict}]  ({result.elapsed_ms} ms)")
        summary_lines.append(
            f"| `{rel}` | \u2014 | `{HA_PRE or 'True'}` | `{HA_POST or 'True'}` "
            f"| **{result.verdict}** | {result.elapsed_ms} ms |"
        )
        if result.verified:
            passed += 1
        else:
            failed += 1
            if result.counterexample:
                print(f"       counterexample: {result.counterexample}")
    else:
        # Parse annotated functions
        specs = _extract_specs_from_source(source)
        if not specs:
            continue  # skip unannotated files silently
        for spec in specs:
            result = verify(
                "",
                pre=spec.pre,
                post=spec.post,
                timeout_ms=HA_TIMEOUT_MS,
            )
            total += 1
            icon   = "\u2705" if result.verified else "\u274c"
            print(
                f"  {icon}  {rel}:{spec.lineno}  {spec.name}()  "
                f"[{result.verdict}]  ({result.elapsed_ms} ms)"
            )
            summary_lines.append(
                f"| `{rel}:{spec.lineno}` | `{spec.name}` | `{spec.pre}` "
                f"| `{spec.post}` | **{result.verdict}** | {result.elapsed_ms} ms |"
            )
            if result.verified:
                passed += 1
            else:
                failed += 1
                if result.counterexample:
                    print(f"       counterexample: {result.counterexample}")

# ── Report ────────────────────────────────────────────────────────────────
print()
all_passed = failed == 0

if total == 0:
    verdict_line = "\u26a0\ufe0f  No annotated triples found."
elif all_passed:
    verdict_line = f"\u2705  All {total} triple(s) verified."
else:
    verdict_line = f"\u274c  {failed} of {total} triple(s) failed."

print(verdict_line)
summary_lines.append("")
summary_lines.append(verdict_line)

_write_output("verified", "true" if all_passed else "false")
_write_output("summary",  verdict_line)
_append_summary("\n".join(summary_lines))

sys.exit(0 if all_passed else 1)
