import httpx
from httpx_sse import aconnect_sse
import asyncio
from typing import AsyncIterator, Optional

class Noa:
    def __init__(self, gateway_url: str = "http://localhost:3000"):
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

    async def execute(self, language: str, code: str, timeout_ms: int = 10000) -> AsyncIterator[dict]:
        """
        POSTs the code execution task to the API gateway, then establishes 
        an SSE live event connection to stream runtime events chunk-by-chunk.
        """
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