"""Ensure the repo root is importable so `backend.*` and `scripts.*` resolve."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
