<#
.SYNOPSIS
    Hoare-Agent local development bootstrap script.

.DESCRIPTION
    Spins up the full Hoare-Agent stack on a local Windows/WSL machine:
      1. Verifies prerequisites (Docker, Python 3.11+, Node 20+).
      2. Optionally pulls and starts a vLLM Docker container with a
         sub-billion-parameter model (Qwen2.5-0.5B-Instruct).
      3. Installs Python backend dependencies.
      4. Installs Node frontend dependencies.
      5. Launches both servers in separate terminal windows (or background
         jobs on headless systems).

.PARAMETER StartLLM
    When set, pulls and starts the vLLM Docker container.

.PARAMETER MockLLM
    Use the built-in mock LLM instead of a real model (no GPU required).

.PARAMETER Model
    The Hugging Face model ID to load into vLLM (default: Qwen/Qwen2.5-0.5B-Instruct).

.EXAMPLE
    .\scripts\bootstrap.ps1 -MockLLM

.EXAMPLE
    .\scripts\bootstrap.ps1 -StartLLM -Model "microsoft/Phi-4-mini-instruct"
#>

[CmdletBinding()]
param (
    [switch]$StartLLM,
    [switch]$MockLLM,
    [string]$Model = "Qwen/Qwen2.5-0.5B-Instruct"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot   = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontDir   = Join-Path $RepoRoot "frontend"

# ── Colour helpers ────────────────────────────────────────────────────────────
function Write-Step  { param($msg) Write-Host "`n▶  $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "   ✓  $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "   ⚠  $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "   ✗  $msg" -ForegroundColor Red; exit 1 }

# ── Prerequisite checks ───────────────────────────────────────────────────────
Write-Step "Checking prerequisites"

# Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) { Write-Fail "Python 3.11+ is required. Install from https://python.org" }
$pyVer = (& $python.Source --version 2>&1) -replace "Python ", ""
if ([version]$pyVer -lt [version]"3.11") { Write-Fail "Python 3.11+ required (found $pyVer)" }
Write-Ok "Python $pyVer"

# Node
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) { Write-Warn "Node.js 20+ not found — frontend will not start." }
else {
    $nodeVer = (node --version) -replace "v", ""
    Write-Ok "Node $nodeVer"
}

# Docker (only if -StartLLM)
if ($StartLLM) {
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $docker) { Write-Fail "Docker is required for --StartLLM. Install from https://docker.com" }
    Write-Ok "Docker $(docker --version)"
}

# ── Python backend setup ──────────────────────────────────────────────────────
Write-Step "Installing Python dependencies"
Push-Location $BackendDir
& $python.Source -m pip install -q -r requirements.txt
Write-Ok "Backend dependencies installed"
Pop-Location

# ── Node frontend setup ───────────────────────────────────────────────────────
if ($node) {
    Write-Step "Installing Node dependencies"
    Push-Location $FrontDir
    npm install --silent
    Write-Ok "Frontend dependencies installed"
    Pop-Location
}

# ── Start vLLM container (optional) ──────────────────────────────────────────
if ($StartLLM) {
    Write-Step "Starting vLLM container (model: $Model)"

    $containerName = "hoare-agent-vllm"
    $running = docker ps --filter "name=$containerName" --format "{{.Names}}"

    if ($running -eq $containerName) {
        Write-Ok "vLLM container already running"
    } else {
        Write-Host "   Pulling vllm/vllm-openai image (this may take a while)…" -ForegroundColor Yellow
        docker run -d `
            --name $containerName `
            --gpus all `
            -p 8000:8000 `
            -e "HUGGING_FACE_HUB_TOKEN=${env:HF_TOKEN}" `
            vllm/vllm-openai:latest `
            --model $Model `
            --dtype float16 `
            --max-model-len 4096 `
            --host 0.0.0.0 `
            --port 8000

        Write-Ok "vLLM container started.  Waiting for it to be ready…"
        $timeout = 120
        $elapsed = 0
        do {
            Start-Sleep -Seconds 5
            $elapsed += 5
            $ready = try {
                $r = Invoke-RestMethod -Uri "http://localhost:8000/v1/models" -TimeoutSec 2
                $r.data.Count -gt 0
            } catch { $false }
        } while (-not $ready -and $elapsed -lt $timeout)

        if (-not $ready) { Write-Warn "vLLM did not become ready within ${timeout}s — check docker logs $containerName" }
        else             { Write-Ok "vLLM ready at http://localhost:8000" }
    }
}

# ── Launch backend ────────────────────────────────────────────────────────────
Write-Step "Starting Hoare-Agent backend (port 8080 / gRPC 50051)"

$env:HOARE_USE_MOCK_LLM = if ($MockLLM) { "1" } else { "0" }
$env:PYTHONPATH = $BackendDir

if ($env:TERM_PROGRAM -or $IsLinux -or $IsMacOS) {
    # Headless / CI — use background jobs
    $backendJob = Start-Job -ScriptBlock {
        param($dir, $py, $mock)
        $env:PYTHONPATH = $dir
        $env:HOARE_USE_MOCK_LLM = $mock
        & $py (Join-Path $dir "main.py")
    } -ArgumentList $BackendDir, $python.Source, $env:HOARE_USE_MOCK_LLM

    Write-Ok "Backend started (job ID $($backendJob.Id))"
} else {
    # Windows — open a new terminal window
    Start-Process powershell -ArgumentList `
        "-NoExit -Command `$env:PYTHONPATH='$BackendDir'; `$env:HOARE_USE_MOCK_LLM='$($env:HOARE_USE_MOCK_LLM)'; cd '$BackendDir'; python main.py"
    Write-Ok "Backend window opened"
}

# ── Launch frontend ───────────────────────────────────────────────────────────
if ($node) {
    Write-Step "Starting React dashboard (port 3000)"

    if ($env:TERM_PROGRAM -or $IsLinux -or $IsMacOS) {
        $frontendJob = Start-Job -ScriptBlock {
            param($dir)
            Set-Location $dir
            npm run dev
        } -ArgumentList $FrontDir

        Write-Ok "Frontend started (job ID $($frontendJob.Id))"
    } else {
        Start-Process powershell -ArgumentList "-NoExit -Command cd '$FrontDir'; npm run dev"
        Write-Ok "Frontend window opened"
    }
}

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "══════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "  Hoare-Agent is running!"                     -ForegroundColor Magenta
Write-Host ""
Write-Host "  Dashboard : http://localhost:3000"           -ForegroundColor Cyan
Write-Host "  Backend   : http://localhost:8080/health"    -ForegroundColor Cyan
Write-Host "  gRPC      : localhost:50051"                 -ForegroundColor Cyan
if ($StartLLM) {
    Write-Host "  vLLM      : http://localhost:8000/v1"   -ForegroundColor Cyan
}
Write-Host "══════════════════════════════════════════════" -ForegroundColor Magenta
