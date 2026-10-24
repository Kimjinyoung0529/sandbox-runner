import json
import subprocess

import pytest

from sandbox_runner import SandboxConfig, SandboxError, Session, SessionManager
from sandbox_runner.cli import main


class FakeDocker:
    def __init__(self):
        self.calls = []
        self.exec_result = subprocess.CompletedProcess([], 0, b"hi\n", b"")

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        if argv[1] == "exec":
            if self.exec_result == "timeout":
                raise subprocess.TimeoutExpired(argv, 1)
            return self.exec_result
        return subprocess.CompletedProcess(argv, 0, b"id\n", b"")


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


def test_defaults_match_aetherion_limits():
    c = SandboxConfig()
    assert (c.memory, c.cpus, c.pids_limit, c.cmd_timeout, c.network) == ("768m", 1.5, 256, 60.0, False)


def test_run_args_have_limits_and_no_network():
    a = SandboxConfig().run_args("x")
    s = " ".join(a)
    for frag in ["--memory 768m", "--cpus 1.5", "--pids-limit 256", "--network none", "--cap-drop ALL", "--read-only", "no-new-privileges"]:
        assert frag in s
    assert any(x.startswith("/work:") for x in a)


def test_network_opt_in():
    assert "none" not in SandboxConfig(network=True).run_args("x")


def test_invalid_config():
    with pytest.raises(ValueError):
        SandboxConfig(cpus=0)


def test_exec_and_timeout_cap():
    d = FakeDocker()
    s = Session(SandboxConfig(), d).start()
    r = s.exec("echo hi", timeout=999)
    assert r.stdout == "hi\n" and r.exit_code == 0 and not r.timed_out
    assert d.calls[-1][3:7] == ["timeout", "-s", "KILL", "60"]


def test_timeout_flags():
    d = FakeDocker()
    s = Session(SandboxConfig(), d).start()
    d.exec_result = subprocess.CompletedProcess([], 137, b"", b"")
    assert s.exec("sleep 99").timed_out
    d.exec_result = "timeout"
    r = s.exec("sleep 99")
    assert r.timed_out and r.exit_code == 137


def test_output_truncated():
    d = FakeDocker()
    d.exec_result = subprocess.CompletedProcess([], 0, b"a" * 100, b"")
    r = Session(SandboxConfig(max_output_bytes=10), d).start().exec("x")
    assert r.truncated and len(r.stdout) == 10


def test_max_sessions_and_idle_reap():
    d, clk = FakeDocker(), Clock()
    m = SessionManager(SandboxConfig(max_sessions=2, idle_timeout=10), d, clk)
    m.open()
    m.open()
    with pytest.raises(SandboxError):
        m.open()
    clk.t = 11
    s3 = m.open()  # idle ones reaped first
    assert len(m) == 1 and m.get(s3.name) is s3
    assert sum(1 for c in d.calls if c[1] == "rm") == 2
    m.close_all()
    assert len(m) == 0


def test_cli_dry_run(capsys):
    assert main(["--dry-run", "echo", "x"]) == 0
    assert "--network" in json.loads(capsys.readouterr().out)
