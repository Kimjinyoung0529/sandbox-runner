"""sandbox-runner: run agent shell commands inside a limited Docker container."""

from .config import SandboxConfig
from .session import ExecResult, SandboxError, Session, SessionManager

__all__ = ["SandboxConfig", "Session", "SessionManager", "ExecResult", "SandboxError"]
__version__ = "0.0.1"
