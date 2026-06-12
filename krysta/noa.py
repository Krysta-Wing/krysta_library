import httpx
from httpx_sse import aconnect_sse
import asyncio
import json
from typing import AsyncIterator, Optional

class Noa:
    def __init__(self, gateway_url: str = "https://kwingclaw.vercel.app"):
        """
        Initializes the Krysta Sandbox execution engine SDK client interface.
        """
        self.gateway_url = gateway_url.rstrip("/")
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        # Open an asynchronous persistent HTTP connection pool block
        self.client = httpx.AsyncClient()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanly sever pool allocation on block departure
        if self.client:
            await self.client.aclose()

    async def execute(self, language: str, code: str = None, code_path: str = None, timeout_ms: int = 10000) -> AsyncIterator[dict]:
        """
        POSTs the code execution task to the API gateway, then establishes 
        an SSE live event connection to stream runtime events chunk-by-chunk.
        """
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


        # 1. Dispatch code payload out to ingestion gateway
        response = await self.client.post(submit_url, json=payload)
        
        # Enhanced debugging check to catch blank or failed gateway hits
        if response.status_code != 202:
            raise RuntimeError(
                f"Gateway Rejected Request.\n"
                f"Status Code: {response.status_code}\n"
                f"Raw Response Content: '{response.text}'"
            )

        try:
            receipt = response.json()
        except Exception as json_err:
            raise RuntimeError(
                f"Gateway returned non-JSON response.\n"
                f"Status Code: {response.status_code}\n"
                f"Raw Response Content: '{response.text}'"
            )

        job_id = receipt.get("jobId")
        
        if not job_id:
            raise ValueError(f"Gateway failed to yield a valid infrastructure jobId transaction receipt token.")

        # 2. Bind directly to the live event telemetry stream bus
        params = {"jobId": job_id}
        
        print(f"[SDK DEBUG] Establishing SSE streaming pipe connection to {stream_url}...")
        
        try:
            # Pass an explicit, prolonged timeout configuration payload to prevent httpx from dropping early
            timeout_config = httpx.Timeout(60.0, connect=10.0)
            
            async with aconnect_sse(self.client, "GET", stream_url, params=params, timeout=timeout_config) as event_stream:
                print("[SDK DEBUG] SSE pipe connection link established. Awaiting daemon frames...")
                async for event in event_stream.aiter_sse():
                    # Yield decoded structured events out to user tracking script loops
                    yield event.json()
                    
        except httpx.TimeoutException as timeout_err:
            raise RuntimeError(f"Streaming telemetry channel timed out waiting for broker response. Details: {timeout_err}")
        except Exception as stream_err:
            raise RuntimeError(f"SSE Telemetry transport layer connection failed. Details: ({type(stream_err).__name__}) {stream_err}")
        
    

#Agent execution...
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
            rules_event = next((e for e in events if e['type'] == 'rules'), None)
            rules = json.loads(rules_event['text']) if rules_event else []

            status = "unknown"
            if stdout_lines:
                try:
                    last_output = json.loads(stdout_lines[-1])
                    status = last_output.get("status", "unknown")
                except Exception:
                    status = "unparseable"

            results.append({
                "name": tc.get("name", tc['input']),
                "status": status,
                "stdout": stdout_lines,
                "rules": rules,
            })

        return results