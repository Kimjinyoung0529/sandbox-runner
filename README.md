# sandbox-runner

에이전트가 내린 셸 명령을 **자원 제한 + 네트워크 없는 Docker 컨테이너** 안에서 실행하는 작은 Python 라이브러리·CLI입니다. AETHERION 오픈소스 묶음의 하나이며, 지금은 **뼈대(v0.0.1)** 단계예요.

A small Python library + CLI that runs agent-issued shell commands inside a **resource-limited, network-less Docker container**. Part of the AETHERION OSS suite. Status: **skeleton (v0.0.1)**.

## 기본 제한 / Default limits

AETHERION 백엔드 샌드박스와 같은 값을 기본으로 씁니다. / Mirrors the AETHERION backend sandbox defaults.

| 항목 / Item | 기본값 / Default |
|---|---|
| memory (swap 포함 동일) | `768m` |
| cpus | `1.5` |
| pids | `256` |
| 명령 타임아웃 / cmd timeout | `60s` (컨테이너 안 `timeout -s KILL` + 호스트 백스톱) |
| network | `none` (opt-in `--network`) |
| 작업 폴더 / work dir | `/work` tmpfs 256m, root FS read-only |
| 권한 / privileges | `--cap-drop ALL`, `no-new-privileges`, user `65534` |
| 유휴 정리 / idle cleanup | 600s |
| 최대 세션 / max sessions | 4 |
| 출력 상한 / output cap | 64 KiB per stream |

## 사용법 / Usage

```bash
pip install -e .
sandbox-runner "echo hello && uname -a"
sandbox-runner --json --timeout 10 "python3 -c 'print(1+1)'"
sandbox-runner --dry-run "true"   # docker run 인자만 출력 / print argv only
```

```python
from sandbox_runner import SandboxConfig, SessionManager

mgr = SessionManager(SandboxConfig(max_sessions=2))
s = mgr.open()
print(s.exec("ls -la /work").stdout)
mgr.reap_idle()   # 유휴 세션 정리 / remove idle sessions
mgr.close_all()
```

## 테스트 / Tests

```bash
pip install -e ".[dev]" && pytest -q -rs
```

단위 테스트는 Docker 없이 가짜 러너로 돌고, 통합 테스트는 Docker 데몬이 없으면 건너뜁니다. / Unit tests use a fake runner; the integration test is skipped when no Docker daemon is available.

성능 수치는 아직 재지 않았어요. 벤치마크는 없습니다. / No benchmarks have been measured yet.

## 보안 주의 / Security caveats (꼭 읽어 주세요)

- **컨테이너는 완벽한 보안 경계가 아닙니다.** 커널을 호스트와 공유하므로 커널·런타임 취약점으로 탈출할 수 있어요. 정말 신뢰할 수 없는 코드라면 gVisor(`--runtime=runsc`), Kata, Firecracker 같은 microVM, 또는 별도 VM을 쓰세요.
- Docker 소켓에 접근할 수 있는 사용자는 사실상 호스트 root입니다. 이 도구를 돌리는 계정을 조심하세요.
- 디스크 쓰기는 tmpfs로 제한하지만, 이미지·로그 등 다른 자원 고갈은 완전히 막지 못합니다.
- `--network`를 켜면 컨테이너가 외부·내부망에 접근할 수 있어요.
- 이 프로젝트는 보안 감사를 받지 않았습니다.

- **Containers are not a perfect isolation boundary.** They share the host kernel; kernel/runtime bugs can allow escape. For truly untrusted code use gVisor, Kata, Firecracker microVMs, or a separate VM.
- Access to the Docker socket is effectively root on the host.
- Writes are confined to tmpfs, but not every form of resource exhaustion is prevented.
- Enabling `--network` gives the container network access.
- This project has not been security-audited.

## License

Apache-2.0 · AETHERION 팀
