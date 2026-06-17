import httpx
from httpx_sse import aconnect_sse
import asyncio
import json
from typing import AsyncIterator, Optional
import uuid
from .trace import ExecutionTrace
from .sandbox import RuleEngine
from .exceptions import KrystaTimeoutError, KrystaGatewayError, KrystaSandboxError

class ExecutionStream:
    def __init__(self, noa_client, language, code, code_path, timeout_ms, session_id):
        self.noa_client = noa_client
        self.language = language
        self.code = code
        self.code_path = code_path
        self.timeout_ms = timeout_ms
        self.session_id = session_id
        self.job_id = None
        self.duration_ms = None
        self._generator = None
        self._events = []

    def __aiter__(self):
        self._generator = self._run_generator()
        return self

    async def __anext__(self):
        return await self._generator.__anext__()

    async def _run_generator(self):
        async for event in self.noa_client._execute_stream(
            self,
            language=self.language,
            code=self.code,
            code_path=self.code_path,
            timeout_ms=self.timeout_ms,
            session_id=self.session_id
        ):
            self._events.append(event)
            yield event

    def __await__(self):
        return self._await_impl().__await__()

    def _trace_from_events(self) -> ExecutionTrace:
        stdout_lines = [
            {"type": "stdout", "text": e.get("text", "")}
            for e in self._events
            if e.get("type") == "stdout" and e.get("text") is not None
        ]
        terminal = next(
            (e["type"] for e in reversed(self._events) if e.get("type") in ("done", "error", "timeout")),
            None,
        )
        exit_code = 0 if terminal == "done" else (-1 if terminal == "error" else None)
        return ExecutionTrace(
            job_id=self.job_id,
            duration_ms=self.duration_ms or 0,
            stdout_lines=stdout_lines,
            exit_code=exit_code,
            timeout_hit=(terminal == "timeout"),
        )

    async def _await_impl(self):
        async for event in self.noa_client._execute_stream(
            self,
            language=self.language,
            code=self.code,
            code_path=self.code_path,
            timeout_ms=self.timeout_ms,
            session_id=self.session_id,
        ):
            self._events.append(event)
        if not self.job_id:
            raise RuntimeError("Connection dropped before a Job ID could be securely assigned.")
        try:
            trace = self.noa_client.trace(self.job_id)
        except (ValueError, OSError):
            trace = self._trace_from_events()
        # Prefer live SSE stdout; fall back to Redis if replay was missed (fast-job race)
        if not trace.stdout_lines and self._events:
            from_events = self._trace_from_events()
            if from_events.stdout_lines:
                trace.stdout_lines = from_events.stdout_lines
        if not trace.stdout_lines and self.job_id:
            await asyncio.sleep(0.3)
            try:
                redis_trace = self.noa_client.trace(self.job_id)
                if redis_trace.stdout_lines:
                    trace.stdout_lines = redis_trace.stdout_lines
                if redis_trace.duration_ms and not trace.duration_ms:
                    trace.duration_ms = redis_trace.duration_ms
            except (ValueError, OSError):
                pass
        if self.duration_ms is not None:
            trace.duration_ms = self.duration_ms
        elif trace.duration_ms == 0 and self._events:
            for e in reversed(self._events):
                if e.get("type") == "metrics" and e.get("text"):
                    try:
                        trace.duration_ms = int(json.loads(e["text"]).get("duration_ms", 0))
                    except Exception:
                        pass
                    break
        if trace.duration_ms == 0 and self.job_id:
            await asyncio.sleep(0.5)
            try:
                redis_trace = self.noa_client.trace(self.job_id)
                if redis_trace.duration_ms:
                    trace.duration_ms = redis_trace.duration_ms
            except (ValueError, OSError):
                pass
        return trace

class Noa:
    def __init__(self, gateway_url: str = "https://app.krystawing.com/"):
        self.gateway_url = gateway_url.rstrip("/")
        self.client: Optional[httpx.AsyncClient] = None
        self._engine = RuleEngine()

    async def __aenter__(self):
        self.client = httpx.AsyncClient()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    def trace(self, job_id: str) -> ExecutionTrace:
        return ExecutionTrace.from_redis(job_id)

    def validate(self, trace: ExecutionTrace) -> dict:
        result = self._engine.validate(trace)

        print("\n[METRICS SUMMARY]")
        print("______________________________")
        print(f"Job Identifier       : {trace.job_id}")
        print(f"Execution Duration   : {trace.duration_ms} ms")
        print(f"Memory Allocation    :  N/A /128 MB")
        print(f"Exit Code            : {trace.exit_code}")
        print("______________________________")
        
        print("\n[SECURITY REPORT]")
        print(json.dumps(result, indent=4))

        return result

    def execute(self, language: str, code: str = None, code_path: str = None, timeout_ms: int = 10000, session_id: str = None):
        return ExecutionStream(self, language, code, code_path, timeout_ms, session_id)

    async def _execute_stream(self, stream_instance, language: str, code: str = None, code_path: str = None, timeout_ms: int = 10000, session_id: str = None) -> AsyncIterator[dict]:
        if code_path and not code:
            with open(code_path, 'r', encoding='utf-8') as f:
                code = f.read()
    
        if not code:
            raise ValueError("Either 'code' or 'code_path' must be provided")
        
        code_size = len(code.encode('utf-8'))
        if code_size > 256 * 1024:
            raise ValueError(f"Code payload exceeds 256KB limit (got {code_size} bytes)")
        
        if not self.client:
            raise RuntimeError("Noa context manager must be entered using 'async with Noa(...) as noa:'")

        submit_url = f"{self.gateway_url}/api/submit"
        stream_url = f"{self.gateway_url}/api/stream"

        payload = {
            "language": language,
            "code": code,
            "timeout_ms": timeout_ms
        }
        if session_id:
            payload["sessionId"] = session_id

        try:
            response = await self.client.post(submit_url, json=payload)
        except httpx.ConnectError as err:
            raise KrystaGatewayError(
                f"Gateway unreachable at {self.gateway_url}.\n"
                f"Details: {err}"
            ) from err
        except httpx.TimeoutException as err:
            raise KrystaGatewayError(
                f"Gateway submit timed out at {self.gateway_url}.\n"
                f"Details: {err}"
            ) from err
        
        if response.status_code != 202:
            raise KrystaGatewayError(
                f"Gateway Rejected Request.\n"
                f"Status Code: {response.status_code}\n"
                f"Raw Response Content: '{response.text}'"
            )

        try:
            receipt = response.json()
        except Exception as json_err:
            raise KrystaGatewayError(
                f"Gateway returned non-JSON response.\n"
                f"Status Code: {response.status_code}\n"
                f"Raw Response Content: '{response.text}'"
            )

        job_id = receipt.get("jobId")
        if not job_id:
            raise KrystaGatewayError("Gateway failed to yield a valid infrastructure jobId transaction receipt token.")

        stream_instance.job_id = job_id
        params = {"jobId": job_id}
        
        try:
            timeout_config = httpx.Timeout(60.0, connect=10.0)
            async with aconnect_sse(self.client, "GET", stream_url, params=params, timeout=timeout_config) as event_stream:
                async for event in event_stream.aiter_sse():
                    data = event.json()
                    if data.get("type") == "stdout_batch" and data.get("text"):
                        try:
                            for line in json.loads(data["text"]):
                                yield {"type": "stdout", "text": line, "timestamp": data.get("timestamp")}
                        except Exception:
                            pass
                        continue
                    if data.get("type") == "metrics" and data.get("text"):
                        try:
                            metrics = json.loads(data["text"])
                            stream_instance.duration_ms = metrics.get("duration_ms", 0)
                        except Exception:
                            pass
                    yield data
        except GeneratorExit:
            return
        except httpx.TimeoutException as timeout_err:
            raise KrystaTimeoutError(f"Streaming telemetry channel timed out waiting for broker response. Details: {timeout_err}")
        except httpx.ConnectError as conn_err:
            raise KrystaGatewayError(
                f"Gateway unreachable during SSE stream at {self.gateway_url}.\n"
                f"Details: {conn_err}"
            ) from conn_err
        except Exception as stream_err:
            raise KrystaGatewayError(f"SSE Telemetry transport layer connection failed. Details: ({type(stream_err).__name__}) {stream_err}")
    async def test_agent(self, code_path: str, test_cases: list, language: str = "python", timeout_ms: int = 5000) -> list:
        with open(code_path, 'r', encoding='utf-8') as f:
            agent_code = f.read()

        results = []
        for tc in test_cases:
            wrapper = agent_code.rstrip() + f"""

import json
try:
    __result = {tc['input']}
    print(json.dumps({{"status": "pass", "result": __result}}))
except Exception as e:
    print(json.dumps({{"status": "fail", "error": str(e)}}))
"""
            events = []
            
            async for event in self.execute(language=language, code=wrapper, timeout_ms=timeout_ms):
                events.append(event)

            stdout_lines = [e['text'] for e in events if e['type'] == 'stdout']
            stderr_lines = [e['text'] for e in events if e['type'] == 'stderr']
            rules_event = next((e for e in events if e['type'] == 'rules'), None)
            rules = json.loads(rules_event['text']) if rules_event else []

            status = "unknown"
            error_detail = None
            if stdout_lines:
                try:
                    last_output = json.loads(stdout_lines[-1])
                    status = last_output.get("status", "unknown")
                except Exception:
                    status = "error"
                    error_detail = "\n".join(stderr_lines) if stderr_lines else f"stdout was not valid JSON: {stdout_lines[-1]}"
            elif stderr_lines:
                status = "error"
                error_detail = "\n".join(stderr_lines)

            results.append({
                "name": tc.get("name", tc['input']),
                "status": status,
                "stdout": stdout_lines,
                "stderr": stderr_lines,
                "error": error_detail,
                "rules": rules,
            })

        return results
    


class Sandbox:
    def __init__(self, client, session_id, language="python"):
        self.client = client
        self.session_id = session_id
        self.language = language
        self.job_id = None

    async def execute(self, code=None, code_path=None, language=None, timeout_ms=10000):
        async for event in self.client.execute(
            code=code,
            code_path=code_path,
            language=language or self.language,
            timeout_ms=timeout_ms,
            session_id=self.session_id,
        ):
            if event.get("type") == "system":
                continue
            yield event


def spawn(runtime="python", session_id=None, gateway_url=None):
    sid = session_id or str(uuid.uuid4())
    return _SpawnContext(runtime, sid, gateway_url)

class _SpawnContext:
    def __init__(self, runtime, session_id, gateway_url=None):
        self.runtime = runtime
        self.session_id = session_id
        self.gateway_url = gateway_url
        self._client = None

    async def __aenter__(self):
        self._client = Noa(gateway_url=self.gateway_url) if self.gateway_url else Noa()
        await self._client.__aenter__()
        return Sandbox(self._client, self.session_id, self.runtime)

    async def __aexit__(self, *args):
        await self._client.__aexit__(*args)

