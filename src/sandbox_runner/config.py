from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SandboxConfig:
    """Limits mirror the AETHERION backend sandbox defaults."""

    image: str = "python:3.12-slim"
    memory: str = "768m"
    cpus: float = 1.5
    pids_limit: int = 256
    cmd_timeout: float = 60.0
    network: bool = False
    workdir: str = "/work"
    tmpfs_size: str = "256m"
    idle_timeout: float = 600.0
    max_sessions: int = 4
    user: str = "65534:65534"
    read_only_root: bool = True
    max_output_bytes: int = 64 * 1024
    docker: str = "docker"
    extra_env: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.cpus <= 0 or self.pids_limit <= 0 or self.cmd_timeout <= 0:
            raise ValueError("cpus, pids_limit and cmd_timeout must be positive")
        if self.max_sessions < 1:
            raise ValueError("max_sessions must be >= 1")

    def run_args(self, name: str) -> list[str]:
        """Build the `docker run` argv that starts an idle sandbox container."""
        args = [
            self.docker, "run", "-d", "--rm",
            "--name", name,
            "--label", "sandbox-runner=1",
            "--memory", self.memory,
            "--memory-swap", self.memory,
            "--cpus", str(self.cpus),
            "--pids-limit", str(self.pids_limit),
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--user", self.user,
            "--tmpfs", f"{self.workdir}:rw,nosuid,nodev,size={self.tmpfs_size},mode=1777",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m,mode=1777",
            "--workdir", self.workdir,
        ]
        if self.read_only_root:
            args.append("--read-only")
        if not self.network:
            args += ["--network", "none"]
        for k, v in sorted(self.extra_env.items()):
            args += ["-e", f"{k}={v}"]
        args += [self.image, "sleep", "infinity"]
        return args
