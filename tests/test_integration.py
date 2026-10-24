import shutil
import subprocess

import pytest

from sandbox_runner import SandboxConfig, Session


def _docker_ok() -> bool:
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


pytestmark = pytest.mark.skipif(not _docker_ok(), reason="docker daemon not available")


def test_real_container():
    with Session(SandboxConfig(image="alpine:3.20", cmd_timeout=5)) as s:
        r = s.exec("echo ok > f && cat f")
        assert r.stdout.strip() == "ok"
        assert s.exec("wget -q -T 2 -O- http://example.com").exit_code != 0  # no network
        assert s.exec("sleep 30", timeout=2).timed_out
