"""Repository-wide pytest bootstrap.

Provenance: 2026-09-14

The HOARE backend is intentionally kept under ``backend/``. This bootstrap
makes that package importable when pytest is invoked from the repository root,
which is how GitHub Actions discovers the repository-wide test suite.
"""

from __future__ import annotations

import sys
from pathlib import Path


BACKEND = Path(__file__).resolve().parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
