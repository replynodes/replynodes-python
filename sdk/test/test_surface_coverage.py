from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SDK_DIR = Path(__file__).resolve().parent.parent


def test_check_surface_coverage_script_passes():
    result = subprocess.run(
        [sys.executable, str(SDK_DIR / "scripts" / "check_surface_coverage.py")],
        cwd=SDK_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Surface coverage OK: 77/77" in result.stdout
