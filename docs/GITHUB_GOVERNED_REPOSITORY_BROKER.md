# HOARE GitHub Governed Repository Broker

**Provenance:** 2026-09-13

## Purpose

This integration extends HOARE from verifying code inside GitHub to governing an authorized agent operating on a customer's GitHub environment.

The authority chain is:

```text
CLIENT GITHUB
      │
 GitHub App / OAuth
      │
      ▼
HOARE GitHub Broker
      │
 ┌────┴────┐
 ▼         ▼
Identity  Repository Scope
 └────┬────┘
      ▼
 AEGIS GitHub Gate
      │
 ┌────┼──────────┐
 ▼    ▼          ▼
ALLOW DENY    ESCALATE
 │
 ▼
HOARE Agent / Agentic DevOps
 │
 ├── Read
 ├── Analyze
 └── Change
       │
       ▼
  Branch / Pull Request
       │
       ▼
 Tests + Proof + Evidence
```

There is deliberately **no direct agent-to-GitHub authority**.

## Customer Permission Model

A customer can grant a narrow repository scope.

Example:

```text
repository: customer/app

READ
  contents
  metadata
  pull requests
  issues

WRITE
  branches
  contents
  pull requests

RESTRICTED
  merge
  deployment
  secrets
```

The implementation maps these grants to `GitHubPermissionSet` and binds them to a tenant and repository through `GitHubRepositoryScope`.

## AEGIS Decisions

### ALLOW

Safe scoped actions such as:

- reading repository metadata
- reading repository contents
- analyzing an authorized repository
- creating a feature branch when branch write permission exists
- writing to an authorized non-production branch
- opening a pull request when pull-request write permission exists

### DENY

Examples:

- repository outside tenant scope
- tenant identity mismatch
- missing customer permission
- secret access
- unrecognized action

### ESCALATE

Examples:

- merge
- deployment
- operations affecting production
- requests targeting production branches

Escalation is not authorization. The action must receive the required explicit human authorization before any future execution layer performs it.

## API Surface

The additive route registrar in `backend/github/app.py` provides:

```text
POST /integrations/github/install
GET  /integrations/github/repositories
GET  /integrations/github/repositories/{owner}/{repo}
POST /integrations/github/analyze
POST /integrations/github/branch
POST /integrations/github/pull-request
POST /integrations/github/action
GET  /integrations/github/audit
```

The existing HOARE HTTP authentication middleware remains the first identity boundary. The GitHub broker is the second boundary, and AEGIS is the action-level authorization boundary.

## Installation

The current additive implementation accepts a GitHub installation credential for development/integration testing and keeps it in process memory only. It never returns the credential and never writes it to the audit log.

Example request shape:

```json
{
  "installation_id": "github-installation-123",
  "repositories": ["customer/app"],
  "permissions": {
    "contents_read": true,
    "metadata_read": true,
    "pull_requests_read": true,
    "issues_read": true,
    "branches_write": true,
    "contents_write": true,
    "pull_requests_write": true,
    "merge": false,
    "deploy": false
  },
  "token": "<installation-credential>"
}
```

For production GitHub App deployment, the credential acquisition/storage layer should be backed by the organization's approved secret-management system and GitHub App installation-token flow. The broker contract intentionally keeps that credential mechanism separate from authorization policy.

## Example Customer Workflow

### Analyze a repository

```text
Customer
  ↓
HOARE tenant identity
  ↓
GitHub repository scope
  ↓
AEGIS ALLOW
  ↓
GitHub Broker
  ↓
Repository contents
  ↓
HOARE analysis
```

### Fix a bug and create a PR

```text
Analyze
  ↓
PLAN
  ↓
GENERATE CHANGE
  ↓
AEGIS: CREATE_BRANCH → ALLOW
  ↓
GitHub branch
  ↓
BUILD / TEST / PROVE
  ↓
AEGIS: CREATE_PULL_REQUEST → ALLOW
  ↓
GitHub PR
  ↓
Audit evidence
```

### Merge/deploy

```text
Agent request
  ↓
AEGIS
  ↓
ESCALATE
  ↓
Human authorization
  ↓
Fresh governed action
```

A prior ALLOW for creating a branch or PR does not authorize a later merge or deployment.

## Security Invariants

1. Agent identity never equals GitHub authority.
2. Tenant identity must match repository scope.
3. Repository access is explicit and scoped.
4. Customer permissions are checked before transport.
5. Secrets are outside the agent boundary.
6. Production branches are escalation boundaries.
7. Merge and deployment are escalation boundaries.
8. Audit events are tenant-scoped.
9. GitHub credentials are never included in audit evidence.
10. AEGIS decisions do not themselves execute GitHub operations.
11. The transport layer cannot manufacture an ALLOW decision.
12. Unknown actions fail closed.

## Relationship to Agentic DevOps

The existing `FARICJH59/HOARE-AGENT/action@v1` proof gate remains useful for CI/CD verification. The broker adds a higher-level control-plane capability:

```text
Before:
GitHub → HOARE verification

After:
GitHub
  ↓
HOARE Broker
  ↓
AEGIS
  ↓
Agentic DevOps
  ↓
Branch / PR
  ↓
Tests / Proof
  ↓
Evidence
```

This makes GitHub one governed execution surface of the broader HOARE control plane rather than making GitHub access a privilege of individual agents.
