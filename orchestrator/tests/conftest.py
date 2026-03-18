from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# The repo .env has restrictive filesystem flags that cause os.stat() to raise
# PermissionError when pydantic-settings tries to load it.  Setting this env-var
# satisfies any Settings() call that touches runtime_persistence_dir, without
# needing to read the .env file.
os.environ.setdefault("ORCHESTRATOR_RUNTIME_PERSISTENCE_DIR", "/tmp/stratos-test-runtime")
