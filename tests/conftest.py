"""Pytest configuration for LOS2026 tests."""

import sys
from pathlib import Path

# Add workspace root to Python path so tests can import modules
workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root))
