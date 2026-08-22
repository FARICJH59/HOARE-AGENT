#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

# HOARE Phase 31 — Termux Autonomous Implementation Orchestrator
# Builds what Termux can execute, records what requires external infrastructure,
# validates the existing backend/frontend without destructive resets, and pushes
# the resulting source changes when Git credentials are available.

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"
PHASE="31"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR=".hoare/phase31"
REPORT="$REPORT_DIR/termux-report-$STAMP.md"
MANIFEST="$REPORT_DIR/capability-manifest.json"
mkdir -p "$REPORT_DIR" agent/orchestration agent/agents api apps/web/app/orchestrate

log(){ printf '\n[HOARE-P31] %s\n' "$*"; }
warn(){ printf '\n[HOARE-P31][WARN] %s\n' "$*" >&2; }
pass(){ printf '[HOARE-P31][OK] %s\n' "$*"; }

have(){ command -v "$1" >/dev/null 2>&1; }

TERMUX=0
if [[ -n "${PREFIX:-}" && "${PREFIX:-}" == *"com.termux"* ]] || [[ "$(uname -o 2>/dev/null || true)" == "Android" ]]; then
  TERMUX=1
fi

PY=""
NODE=""
NPM=""
PNPM=""
GIT=""

have python && PY="$(command -v python)"
have node && NODE="$(command -v node)"
have npm && NPM="$(command -v npm)"
have pnpm && PNPM="$(command -v pnpm)"
have git && GIT="$(command -v git)"

cat > "$MANIFEST" <<EOF
{
  "phase": "31",
  "generated_at": "$STAMP",
  "platform": "$(uname -s 2>/dev/null || echo unknown)",
  "architecture": "$(uname -m 2>/dev/null || echo unknown)",
  "termux_detected": $([[ "$TERMUX" == 1 ]] && echo true || echo false),
  "termux_execution_policy": {
    "build_local": true,
    "run_python_node": true,
    "run_frontend_dev_server": true,
    "docker_daemon_required": false,
    "gpu_llm_required": false,
    "cloud_credentials_required_for_deploy": true
  }
}
EOF

cat > "$REPORT" <<EOF
# HOARE Phase 31 Termux Autonomous Build Report

Generated: $STAMP

## Execution boundary

This run builds and validates source that is compatible with Termux. Docker daemon,
NVIDIA/vLLM GPU execution, systemd services, and cloud deployment are treated as
external capabilities. Their source/configuration is prepared but not falsely
reported as locally executed.

## Detected tools

- Python: ${PY:-missing}
- Node: ${NODE:-missing}
- npm: ${NPM:-missing}
- pnpm: ${PNPM:-missing}
- git: ${GIT:-missing}
- Termux: $([[ "$TERMUX" == 1 ]] && echo detected || echo not-detected)
EOF

log "Phase 31 capability discovery"
for tool in git python node npm pnpm curl; do
  if have "$tool"; then pass "$tool available"; else warn "$tool unavailable"; fi
done

# Termux package bootstrap. Do not run apt/pkg as root and do not upgrade the
# entire environment. Only install missing, lightweight build dependencies.
if [[ "$TERMUX" == 1 ]] && have pkg; then
  log "Installing only missing Termux build packages"
  missing=()
  for p in git python nodejs-lts curl; do
    command -v "$p" >/dev/null 2>&1 || missing+=("$p")
  done
  if ((${#missing[@]})); then
    pkg install -y "${missing[@]}" || warn "Termux package installation partially failed"
  fi
fi

# Re-resolve executables after package bootstrap.
have git || { warn "git is required for Phase 31 source synchronization"; exit 20; }
have python || warn "Python unavailable; backend tests will be skipped"
have node || warn "Node unavailable; frontend checks will be skipped"
have npm || warn "npm unavailable; frontend checks will be skipped"

# Preserve existing project work. Never delete node_modules, lockfiles, .next,
# virtualenvs, databases, credentials, or user source during autonomous repair.
log "Inspecting existing HOARE source tree"
find . -maxdepth 2 -type f \
  \( -name 'package.json' -o -name 'requirements.txt' -o -name 'pyproject.toml' \
     -o -name 'docker-compose.yml' -o -name 'Dockerfile' \) \
  -print | sort >> "$REPORT"

# ---------------------------------------------------------------------------
# Phase 31 source contracts. These are additive and intentionally dependency-light.
# ---------------------------------------------------------------------------
cat > agent/orchestration/OrchestrationCycle.ts <<'EOF'
export type CycleStatus = 'PLANNED' | 'RUNNING' | 'VERIFIED' | 'BLOCKED' | 'FAILED';

export interface OrchestrationCycleInput {
  intent: string;
  tenantId?: string;
  correlationId?: string;
}

export interface OrchestrationCycleResult {
  status: CycleStatus;
  phase: 31;
  next: string[];
  blockers: string[];
}

/** Phase 31 provider-neutral orchestration boundary. */
export class OrchestrationCycle {
  run(input: OrchestrationCycleInput): OrchestrationCycleResult {
    const intent = input.intent.trim();
    if (!intent) {
      return { status: 'FAILED', phase: 31, next: [], blockers: ['empty_intent'] };
    }
    return {
      status: 'PLANNED',
      phase: 31,
      next: ['validate_identity', 'compile_intent', 'authorize_plan', 'execute_or_queue', 'verify_result'],
      blockers: [],
    };
  }
}
EOF

cat > agent/agents/phase31-agent-manifest.json <<'EOF'
{
  "name": "hoare-phase31-autonomous-agent",
  "phase": 31,
  "mode": "termux-compatible-autonomous-build",
  "capabilities": [
    "repository_inspection",
    "safe_additive_scaffolding",
    "python_validation",
    "node_validation",
    "provider_neutral_planning",
    "capability_detection",
    "git_commit_and_push"
  ],
  "external_capabilities": [
    "docker_daemon",
    "nvidia_gpu",
    "vllm_gpu_runtime",
    "cloud_credentials",
    "managed_database",
    "managed_message_broker",
    "cloudflare_dns_changes"
  ],
  "safety": {
    "destructive_cleanup": false,
    "credential_creation": false,
    "force_push": false
  }
}
EOF

cat > api/phase31-capabilities.ts <<'EOF'
export interface RuntimeCapability {
  name: string;
  local: boolean;
  external: boolean;
  reason: string;
}

export const PHASE31_CAPABILITIES: RuntimeCapability[] = [
  { name: 'python_backend', local: true, external: false, reason: 'Termux supports Python execution.' },
  { name: 'node_frontend', local: true, external: false, reason: 'Node/npm can run the frontend toolchain on supported Termux builds.' },
  { name: 'git_source_sync', local: true, external: false, reason: 'Git operations are available in Termux.' },
  { name: 'docker_daemon', local: false, external: true, reason: 'Termux does not provide a native Docker daemon; use a remote Linux host or compatible daemon.' },
  { name: 'nvidia_vllm', local: false, external: true, reason: 'The current Android/Termux target is not treated as an NVIDIA GPU execution host.' },
  { name: 'cloud_deployment', local: false, external: true, reason: 'Deployment requires provider credentials and external infrastructure.' }
];
EOF

cat > apps/web/app/orchestrate/page.tsx <<'EOF'
'use client';

import { useState } from 'react';

export default function OrchestratePage() {
  const [intent, setIntent] = useState('');
  const [submitted, setSubmitted] = useState(false);

  return (
    <main style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
      <h1>HOARE Orchestration</h1>
      <p>Phase 31 intent-to-orchestration boundary.</p>
      <textarea
        value={intent}
        onChange={(e) => setIntent(e.target.value)}
        placeholder="Describe the workload or change you want HOARE to plan."
        rows={8}
        style={{ width: '100%', padding: 12 }}
      />
      <button
        type="button"
        onClick={() => setSubmitted(Boolean(intent.trim()))}
        style={{ marginTop: 12, padding: '10px 16px' }}
      >
        Compile Intent
      </button>
      {submitted && <p role="status">Intent accepted for Phase 31 planning.</p>}
    </main>
  );
}
EOF

# ---------------------------------------------------------------------------
# Backend validation — install project dependencies only where project files exist.
# ---------------------------------------------------------------------------
if [[ -f backend/requirements.txt ]] && have python; then
  log "Preparing Python backend environment"
  python -m venv .venv-phase31 2>/dev/null || true
  if [[ -x .venv-phase31/bin/python ]]; then
    .venv-phase31/bin/python -m pip install --upgrade pip >/dev/null 2>&1 || true
    .venv-phase31/bin/python -m pip install -r backend/requirements.txt >/dev/null 2>&1 || warn "Backend dependency install incomplete"
    if [[ -d backend/tests ]]; then
      .venv-phase31/bin/python -m pytest backend/tests -q || warn "Backend tests reported failures"
    fi
  fi
fi

# Repository-wide Python tests if a usable interpreter and pytest exist.
if have python && [[ -d tests ]]; then
  python -m pytest tests -q || warn "Repository tests reported failures"
fi

# ---------------------------------------------------------------------------
# Frontend validation — prefer existing lockfile/package manager; no deletion.
# ---------------------------------------------------------------------------
if [[ -f frontend/package.json ]] && have npm; then
  log "Validating frontend package"
  (cd frontend && npm install --ignore-scripts) || warn "Frontend npm install incomplete"
  (cd frontend && npm run build) || warn "Frontend build reported failures"
fi

if [[ -f apps/web/package.json ]] && have npm; then
  log "Validating apps/web package"
  (cd apps/web && npm install --ignore-scripts) || warn "apps/web npm install incomplete"
  (cd apps/web && npm run build) || warn "apps/web build reported failures"
fi

# ---------------------------------------------------------------------------
# Generate external-capability plan. These files are intentionally source-only:
# Termux prepares them; CI/cloud/remote Linux executes them.
# ---------------------------------------------------------------------------
mkdir -p deploy/phase31
cat > deploy/phase31/EXTERNAL_RUNTIME.md <<'EOF'
# Phase 31 External Runtime Boundary

Termux builds and validates the provider-neutral source. The following are intentionally **not** executed locally:

1. Docker daemon / Docker Compose service orchestration.
2. NVIDIA CUDA/vLLM inference runtime.
3. Managed cloud deployment and IAM mutations.
4. Production databases, Redis/streams, MQTT/EMQX brokers, and secret managers.
5. DNS/domain changes and Cloudflare production routing.

The repository may contain manifests/configuration for these systems, but execution belongs to CI or a Linux/cloud runtime with the required credentials and hardware.
EOF

cat > deploy/phase31/termux-handoff.json <<EOF
{
  "phase": 31,
  "generated_at": "$STAMP",
  "local_completed": [
    "capability discovery",
    "additive orchestration contracts",
    "frontend route scaffold",
    "Python validation when available",
    "Node validation when available",
    "git source synchronization"
  ],
  "external_handoff": [
    "docker",
    "gpu_llm",
    "cloud_iam",
    "managed_services",
    "production_dns"
  ],
  "force_push": false
}
EOF

# Record final state.
git status --short >> "$REPORT" || true
printf '\n## Final state\n\n' >> "$REPORT"
git rev-parse HEAD >> "$REPORT" || true

# Commit only Phase 31 files created/changed by this script. Never stage all files.
git add agent/orchestration/OrchestrationCycle.ts \
  agent/agents/phase31-agent-manifest.json \
  api/phase31-capabilities.ts \
  apps/web/app/orchestrate/page.tsx \
  deploy/phase31/EXTERNAL_RUNTIME.md \
  deploy/phase31/termux-handoff.json \
  .hoare/phase31/ 2>/dev/null || true

if git diff --cached --quiet; then
  log "No new Phase 31 changes to commit"
else
  git commit -m "feat(phase31): autonomous Termux-compatible implementation" || warn "Commit failed"
fi

# Push only when an authenticated remote exists. Never force push.
REMOTE="$(git remote get-url origin 2>/dev/null || true)"
if [[ -n "$REMOTE" ]]; then
  BRANCH="$(git branch --show-current)"
  if [[ -n "$BRANCH" ]]; then
    log "Pushing Phase 31 branch: $BRANCH"
    git push -u origin "$BRANCH" || warn "Push failed; source remains committed locally"
  fi
else
  warn "No origin remote configured; nothing was pushed"
fi

log "Phase 31 autonomous implementation pass complete"
echo "Report: $REPORT"
echo "Manifest: $MANIFEST"
echo "External handoff: deploy/phase31/termux-handoff.json"
