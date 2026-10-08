import os
import shutil
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "setup.sh"


def test_lifecycle_commands_do_not_accept_environment_argument():
    status = subprocess.run(
        [SCRIPT, "status"], text=True, capture_output=True, check=False
    )
    rejected = subprocess.run(
        [SCRIPT, "status", "dev"], text=True, capture_output=True, check=False
    )

    assert status.returncode == 0
    assert "版本" in status.stdout
    assert rejected.returncode == 1
    assert "usage:" in rejected.stderr


def test_start_and_stop_manage_the_installed_command(tmp_path):
    repo = tmp_path / "repo"
    script = repo / "scripts" / "setup.sh"
    script.parent.mkdir(parents=True)
    shutil.copy2(SCRIPT, script)
    fake_cli = tmp_path / "bin" / "fartask"
    fake_cli.parent.mkdir()
    fake_cli.write_text("#!/usr/bin/env bash\nexec sleep 30\n")
    fake_cli.chmod(0o755)
    env = os.environ | {"PATH": f"{fake_cli.parent}:{os.environ['PATH']}"}

    started = subprocess.run(
        [script, "start"], text=True, capture_output=True, check=False, env=env
    )
    try:
        status = subprocess.run(
            [script, "status"], text=True, capture_output=True, check=False, env=env
        )
        assert started.returncode == 0, started.stderr
        assert "运行中" in status.stdout
    finally:
        stopped = subprocess.run(
            [script, "stop"], text=True, capture_output=True, check=False, env=env
        )

    assert stopped.returncode == 0
    assert "已停止" in stopped.stdout
