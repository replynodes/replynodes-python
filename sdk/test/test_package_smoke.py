from __future__ import annotations

import subprocess
import sys
import tempfile
import venv
from pathlib import Path

import pytest

SDK_DIR = Path(__file__).resolve().parent.parent


@pytest.mark.slow
def test_wheel_builds_and_installs_cleanly_and_exposes_public_api():
    with tempfile.TemporaryDirectory(prefix="replynodes-sdk-smoke-") as tmp:
        tmp_path = Path(tmp)
        dist_dir = tmp_path / "dist"

        build = subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist_dir), str(SDK_DIR)],
            capture_output=True,
            text=True,
        )
        assert build.returncode == 0, build.stdout + build.stderr

        wheels = list(dist_dir.glob("replynodes-*.whl"))
        assert len(wheels) == 1, f"expected exactly one wheel, found {wheels}"

        venv_dir = tmp_path / "venv"
        venv.create(venv_dir, with_pip=True)
        venv_python = venv_dir / "bin" / "python"

        install = subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--quiet", str(wheels[0])],
            capture_output=True,
            text=True,
        )
        assert install.returncode == 0, install.stdout + install.stderr

        check = subprocess.run(
            [
                str(venv_python),
                "-c",
                (
                    "import replynodes; "
                    "from replynodes.dx import ReplyNodes, ReplyNodesError, ReplyNodesTimeoutError, PUBLIC_OPERATION_REGISTRY; "
                    "client = ReplyNodes(api_key='placeholder', base_url='https://test.invalid'); "
                    "assert callable(client.youtube.search); "
                    "assert client.web.search is client.google.search; "
                    "assert len(PUBLIC_OPERATION_REGISTRY) == 13; "
                    "print('ok')"
                ),
            ],
            capture_output=True,
            text=True,
        )
        assert check.returncode == 0, check.stdout + check.stderr
        assert check.stdout.strip() == "ok"
