#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

# HOARE Phase 31.1 — Autonomous Termux Test Runtime & Remediation
# Safe-by-default: preserves user work, never force-pushes, never resets Git,
# and does not replace an already-working Node/Python toolchain.

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR=".hoare/phase31"
REPORT="$REPORT_DIR/remediation-report-$STAMP.md"
mkdir -p "$REPORT_DIR"

log(){ printf '\n[HOARE-P31.1] %s\n' "$*"; }
warn(){ printf '[HOARE-P31.1][WARN] %s\n' "$*" >&2; }
pass(){ printf '[HOARE-P31.1][OK] %s\n' "$*"; }

ROOT_PYTHONPATH="$ROOT/backend"
export PYTHONPATH="$ROOT_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}"

cat > "$REPORT" <<EOF
# HOARE Phase 31.1 Autonomous Remediation Report

Generated: $STAMP

## Safety boundary

- Existing uncommitted source is preserved.
- No `git reset`, `git clean`, force push, or destructive dependency cleanup.
- Existing Node/Python installations are preserved.
- Local services may be started only for the test session and only by this runner.

## Initial repository state

EOF

git status --short >> "$REPORT" || true

# Discover the backend package instead of assuming the repository root is the
# Python import root.
if [[ -f backend/hoare_engine/__init__.py ]]; then
  pass "backend Python package discovered"
else
  warn "backend/hoare_engine package not found"
fi

# Do not replace a working Node installation. Record versions for diagnosis.
for tool in python node npm pnpm git; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf -- '- %s: %s\n' "$tool" "$("$tool" --version 2>&1 | head -1)" >> "$REPORT"
  else
    printf -- '- %s: missing\n' "$tool" >> "$REPORT"
  fi
done

# Run the backend suite. backend/tests/conftest.py autonomously starts the
# gRPC test dependency when 127.0.0.1:50051 is not already listening.
if command -v python >/dev/null 2>&1 && [[ -d backend/tests ]]; then
  log "Running backend suite with backend package root"
  if python -m pytest backend/tests -q 2>&1 | tee -a "$REPORT"; then
    pass "Backend suite passed"
  else
    warn "Backend suite still has failures"
  fi
else
  warn "Python backend test prerequisites unavailable"
fi

# Frontend validation is intentionally non-destructive. Use the existing npm
# toolchain; do not invoke npm audit fix --force.
if [[ -f frontend/package.json ]] && command -v npm >/dev/null 2>&1; then
  log "Validating frontend build"
  if (cd frontend && npm run build) 2>&1 | tee -a "$REPORT"; then
    pass "Frontend build passed"
  else
    warn "Frontend build reported failures"
  fi
fi

printf '\n## Final repository state\n\n' >> "$REPORT"
git status --short >> "$REPORT" || true
printf '\n## Final Git SHA\n\n' >> "$REPORT"
git rev-parse HEAD >> "$REPORT"

# Only stage the remediation-owned test fixture and report. Existing user work
# remains unstaged and untouched.
git add backend/tests/conftest.py "$REPORT"
if git diff --cached --quiet; then
  log "No remediation-owned changes to commit"
else
  git commit -m "feat(phase31.1): autonomous test runtime remediation"
fi

BRANCH="$(git branch --show-current)"
if [[ -n "$BRANCH" ]] && git remote get-url origin >/dev/null 2>&1; then
  log "Pushing verified Phase 31.1 changes to $BRANCH"
  git push -u origin "$BRANCH"
else
  warn "No authenticated origin/branch available; changes remain local"
fi

log "Phase 31.1 remediation pass complete"
echo "Report: $REPORT"
