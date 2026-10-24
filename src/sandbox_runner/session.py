from __future__ import annotations

import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Callable

from .config import SandboxConfig

Runner = Callable[..., subprocess.CompletedProcess]


class SandboxError(RuntimeError):
    pass


@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    duration: float
    truncated: bool = False


def _clip(data: bytes, limit: int) -> tuple[str, bool]:
    if len(data) > limit:
        return data[:limit].decode("utf-8", "replace"), True
    return data.decode("utf-8", "replace"), False


class Session:
    def __init__(self, config: SandboxConfig, runner: Runner = subprocess.run, clock: Callable[[], float] = time.monotonic):
        self.config = config
        self.name = f"sbx-{uuid.uuid4().hex[:12]}"
        self._run = runner
        self._clock = clock
        self.started = False
        self.last_used = clock()

    def start(self) -> "Session":
        p = self._run(self.config.run_args(self.name), capture_output=True, timeout=120)
        if p.returncode != 0:
            raise SandboxError(f"docker run failed: {p.stderr!r}")
        self.started = True
        self.last_used = self._clock()
        return self

    def exec(self, command: str, timeout: float | None = None) -> ExecResult:
        if not self.started:
            raise SandboxError("session not started")
        t = timeout if timeout is not None else self.config.cmd_timeout
        t = min(t, self.config.cmd_timeout)
        # `timeout` inside the container kills the process tree; the host-side
        # timeout is a backstop in case docker exec itself hangs.
        argv = [self.config.docker, "exec", self.name, "timeout", "-s", "KILL", str(int(max(1, t))), "sh", "-c", command]
        t0 = self._clock()
        timed_out = False
        try:
            p = self._run(argv, capture_output=True, timeout=t + 5)
            code, out_b, err_b = p.returncode, p.stdout or b"", p.stderr or b""
            if code in (124, 137):
                timed_out = True
        except subprocess.TimeoutExpired as e:
            timed_out, code = True, 137
            out_b, err_b = e.stdout or b"", e.stderr or b""
        self.last_used = self._clock()
        out, tr1 = _clip(out_b, self.config.max_output_bytes)
        err, tr2 = _clip(err_b, self.config.max_output_bytes)
        return ExecResult(code, out, err, timed_out, self.last_used - t0, tr1 or tr2)

    def idle_for(self) -> float:
        return self._clock() - self.last_used

    def close(self) -> None:
        if self.started:
            self._run([self.config.docker, "rm", "-f", self.name], capture_output=True, timeout=60)
            self.started = False

    def __enter__(self) -> "Session":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.close()


class SessionManager:
    """Keeps at most `max_sessions` sandboxes and removes idle ones."""

    def __init__(self, config: SandboxConfig | None = None, runner: Runner = subprocess.run, clock: Callable[[], float] = time.monotonic):
        self.config = config or SandboxConfig()
        self._runner = runner
        self._clock = clock
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def open(self) -> Session:
        with self._lock:
            self._reap_locked()
            if len(self._sessions) >= self.config.max_sessions:
                raise SandboxError(f"max_sessions ({self.config.max_sessions}) reached")
            s = Session(self.config, self._runner, self._clock).start()
            self._sessions[s.name] = s
            return s

    def get(self, name: str) -> Session:
        with self._lock:
            if name not in self._sessions:
                raise SandboxError(f"unknown session {name}")
            return self._sessions[name]

    def close(self, name: str) -> None:
        with self._lock:
            s = self._sessions.pop(name, None)
        if s:
            s.close()

    def reap_idle(self) -> list[str]:
        with self._lock:
            return self._reap_locked()

    def _reap_locked(self) -> list[str]:
        dead = [n for n, s in self._sessions.items() if s.idle_for() > self.config.idle_timeout]
        for n in dead:
            self._sessions.pop(n).close()
        return dead

    def close_all(self) -> None:
        with self._lock:
            names = list(self._sessions)
        for n in names:
            self.close(n)

    def __len__(self) -> int:
        return len(self._sessions)
