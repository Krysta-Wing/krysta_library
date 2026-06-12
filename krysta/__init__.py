import json
import httpx
import asyncio
from typing import AsyncGenerator
from .trace import ExecutionTrace
from .sandbox import RuleEngine

class Noa:
    """The primary public entrypoint for the Krysta NoA SDK ecosystem."""
    def __init__(self, gateway_url: str = "http://localhost:3000" or "https://kwing.vercel.app/"):
        self.gateway_url = gateway_url
        self._engine = RuleEngine()

    def spawn(self, language: str, code: str):
        return NoaExecutionLifecycle(self.gateway_url, language, code)

    def trace(self, job_id: str) -> ExecutionTrace:
        """
        Fetches the final ExecutionTrace for a completed job from Redis.
        """
        return ExecutionTrace.from_redis(job_id)

    def validate(self, trace: ExecutionTrace) -> dict:
        """
        Passes an ExecutionTrace through the sandbox RuleEngine validator.
        """
        return self._engine.validate(trace)

    async def execute(self, language: str, code: str) -> ExecutionTrace:
        """
        High-level orchestration method that automatically posts a job, consumes
        and exhausts the live streaming frames, and resolves into a full ExecutionTrace.
        """
        lifecycle = self.spawn(language, code)

        try:
            async with lifecycle as stream:
                async for _ in stream:
                    # Consume all frames including metrics — lifecycle stores them internally
                    pass
        except httpx.ReadError:
            print(f"\n[SDK WARNING] Telemetry pipe disrupted or closed early by server.")

        job_id = lifecycle.job_id

        if job_id:
            print(f"[SDK INFO] Fetching final validation metric traces for Job ID: {job_id}...")
            # FIX: call self.trace() which delegates to ExecutionTrace.from_redis()
            trace = self.trace(job_id)

            # FIX: backfill duration_ms from the metrics frame captured during streaming
            if lifecycle.duration_ms is not None:
                trace.duration_ms = lifecycle.duration_ms

            return trace
        else:
            raise RuntimeError("[SDK ERROR] Connection dropped before a Job ID could be securely assigned.")


class NoaExecutionLifecycle:
    """Handles the inner stateful scope of an active streaming execution task connection."""
    def __init__(self, gateway_url: str, language: str, code: str):
        self.gateway_url = gateway_url
        self.language = language
        self.code = code
        self.job_id = None
        self.duration_ms = None  # FIX: capture metrics frame duration here

    async def __aenter__(self):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.gateway_url}/api/submit",
                json={"language": self.language, "code": self.code}
            )
            response.raise_for_status()
            payload = response.json()
            self.job_id = payload.get("jobId")

        return self._stream_generator()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def _stream_generator(self) -> AsyncGenerator[dict, None]:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", f"{self.gateway_url}/api/stream?jobId={self.job_id}") as response:
                print("[SDK DEBUG] SSE Stream link connected! Awaiting incoming frames from background worker...")
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        try:
                            frame = json.loads(line[5:])
                            print(f"[SDK DEBUG] Received frame type: {frame.get('type')}")

                            # FIX: capture duration_ms from metrics frame before yielding
                            if frame.get("type") == "metrics" and frame.get("text"):
                                try:
                                    metrics = json.loads(frame["text"])
                                    self.duration_ms = metrics.get("duration_ms", 0)
                                except Exception as e:
                                    print(f"[SDK WARNING] Failed to parse metrics frame: {e}")

                            yield frame

                            if frame.get("type") in ["done", "timeout", "error"]:
                                print("[SDK DEBUG] Terminal lifecycle frame detected. Closing stream context connection.")
                                break
                        except Exception as e:
                            print(f"[SDK DEBUG] Failed to parse frame line: {e}")
                            continue

                        