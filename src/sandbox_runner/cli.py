from __future__ import annotations

import argparse
import json
import sys

from .config import SandboxConfig
from .session import Session


def build_parser() -> argparse.ArgumentParser:
    d = SandboxConfig()
    p = argparse.ArgumentParser(prog="sandbox-runner", description="Run a shell command in a limited Docker sandbox")
    p.add_argument("command", nargs="+", help="shell command (joined with spaces, run via sh -c)")
    p.add_argument("--image", default=d.image)
    p.add_argument("--memory", default=d.memory)
    p.add_argument("--cpus", type=float, default=d.cpus)
    p.add_argument("--pids", type=int, default=d.pids_limit)
    p.add_argument("--timeout", type=float, default=d.cmd_timeout)
    p.add_argument("--network", action="store_true", help="allow network (default: none)")
    p.add_argument("--json", action="store_true", help="print result as JSON")
    p.add_argument("--dry-run", action="store_true", help="print the docker run argv and exit")
    return p


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    cfg = SandboxConfig(image=a.image, memory=a.memory, cpus=a.cpus, pids_limit=a.pids, cmd_timeout=a.timeout, network=a.network)
    if a.dry_run:
        print(json.dumps(cfg.run_args("sbx-dry-run")))
        return 0
    with Session(cfg) as s:
        r = s.exec(" ".join(a.command))
    if a.json:
        print(json.dumps(r.__dict__, ensure_ascii=False))
    else:
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        if r.timed_out:
            sys.stderr.write(f"\n[sandbox-runner] timed out after {cfg.cmd_timeout}s\n")
    return r.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
