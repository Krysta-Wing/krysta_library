# Krysta NoA — Python SDK

![logo](assets/noa.png)

Krysta NoA lets you execute AI-agent-generated code safely. Every run happens inside an isolated Docker container — no network access, capped memory, read-only filesystem, non-root user — with live streaming output and automatic safety checks.

## Installation

```bash
pip install krysta
```

## Quickstart

```python
import asyncio
from krysta.noa import Noa

async def main():
    async with Noa() as client:
        async for event in client.execute(language="python", code="print('hello world')"):
            print(event)

asyncio.run(main())
```

---

## Core concepts

### `Noa`

The main client. Connects to the Krysta execution gateway and streams results back over SSE.

```python
from krysta.noa import Noa

async with Noa() as client:
    ...
```

By default, connects to the hosted Krysta gateway. To use your own gateway (self-hosted), pass `gateway_url`:

```python
async with Noa(gateway_url="https://your-gateway.example.com") as client:
    ...
```

### `execute()`

Runs a piece of code inside the sandbox and streams events back as it runs.

```python
async def execute(
    language: str = "python",
    code: str = None,
    code_path: str = None,
    timeout_ms: int = 10000,
    session_id: str = None,
) -> AsyncIterator[dict]
```

**Parameters**

- `language` — `"python"` or `"javascript"`
- `code` — a string of source code to run
- `code_path` — alternatively, a path to a local file whose contents will be sent and run. Max 256KB.
- `timeout_ms` — max execution time before the process is killed (default 10000ms, max 60000ms)
- `session_id` — if set, gives this run a persistent workspace at `/workspace` shared across calls with the same `session_id`. Without it, the sandbox is stateless and the filesystem is locked down.

Either `code` or `code_path` must be provided.

### `spawn()` — stateful sessions

For multi-step workflows (an agent writing code, testing it, fixing it, rerunning), use `spawn()` to get a sandbox tied to a persistent session:

```python
from krysta.noa import spawn

async with spawn(runtime="python", session_id="agent_turn_1") as sandbox:
    async for event in sandbox.execute(code="with open('data.txt','w') as f: f.write('hello')"):
        print(event)

    # A later call with the same session_id can read data.txt back
    async for event in sandbox.execute(code="with open('data.txt') as f: print(f.read())"):
        print(event)
```

Within a session, filesystem access is allowed but confined to `/workspace` inside the container — nothing outside it is reachable, and network access remains disabled regardless of session state.

### `test_agent()`

Given a file containing one or more functions, run a list of test cases against it inside the sandbox:

```python
async with Noa() as client:
    results = await client.test_agent(
        code_path="agent_output.py",
        test_cases=[
            {"name": "normal case", "input": "calculate_stats([1,2,3,4,5])"},
            {"name": "empty list", "input": "calculate_stats([])"},
        ]
    )
    for r in results:
        print(r["name"], "->", r["status"])
```

Each test case's `input` is a Python expression calling a function defined in `code_path`. Results report `"pass"` or `"fail"` per case, along with stdout and rule results.

---

## Streaming events

Every `execute()` call yields a sequence of event dicts:

```json
{"type": "system" | "stdout" | "stderr" | "rules" | "done" | "timeout" | "error", "text": "...", "timestamp": 1234567890}
```

- **`system`** — lifecycle markers, e.g. `"EXECUTION_STARTED"`
- **`stdout`** / **`stderr`** — output lines as they're produced, streamed live
- **`rules`** — emitted once near the end; `text` is a JSON string of rule results (see below)
- **`done`** — the run finished and exited cleanly (exit code 0)
- **`timeout`** — the run exceeded `timeout_ms` and was killed
- **`error`** — the run failed (non-zero exit, blocked before running, or an infrastructure error)

---

## Safety rules

Every run is checked against a fixed set of rules. Results are returned in the `rules` event as a JSON list:

```json
[{"rule": "NoNetworkCallsRule", "result": "PASS", "reason": "...", "category": "security"}, ...]
```

**Security rules** (these determine whether a run is safe):

| Rule | What it checks |
|---|---|
| `NoNetworkCallsRule` | No outbound network calls were made or attempted |
| `ExitCodeZeroRule` | The process exited cleanly (code 0) |
| `MemoryLimitRule` | Memory stayed under the 128MB container limit |
| `NoFilesystemAccessRule` | No filesystem access outside `/workspace` (or none at all, if no session) |

**Optional / informational rules** (don't affect whether a run is "safe", just describe the output):

| Rule | What it checks |
|---|---|
| `ValidJsonRule` | Whether stdout is a single valid JSON document |

---

## PyPI

[https://pypi.org/project/krysta/](https://pypi.org/project/krysta/)