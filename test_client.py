import os
import sys
import json
import asyncio
from google import genai
from google.genai import types
from google.genai.errors import APIError

# 🟢 IMPORTING DIRECT FROM YOUR VERIFIED PATH
try:
    from krysta.noa import Noa
    print("SYSTEM // KWING // Live PyPI 'krysta.noa.Noa' successfully bound.")
except ImportError as e:
    print(f"CRITICAL // Failed to import 'Noa' from 'krysta.noa'.\nDetails: {e}")
    sys.exit(1)

GATEWAY_URL = "http://localhost:3000"

# Resilient helper to handle 503 spikes gracefully
async def generate_with_retry(client, model, contents, config, max_retries=5, base_delay=2):
    for attempt in range(max_retries):
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=contents,
                config=config
            )
            return response
        except APIError as api_err:
            if api_err.code == 503 and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"⚠️ SYSTEM // GEMINI 503 BUSY // Retrying generation loop in {delay}s...")
                await asyncio.sleep(delay)
            else:
                raise api_err

async def run_hardcore_agent_test():
    if "GEMINI_API_KEY" not in os.environ:
        print("CRITICAL // GEMINI_API_KEY environment variable missing.")
        sys.exit(1)

    ai_client = genai.Client()
    print("\n============================================================")
    print("🔥 STARTING HARDCORE AGENT SELF-CORRECTION PROFILE TEST")
    print("============================================================\n")

    agent_task = (
        "Write a short Python snippet that reads a mock list of strings representing numeric values: "
        "['10', '20', 'invalid_data', '40']. The script MUST use a direct integer cast int() inside a list comprehension "
        "without a try/catch, so that it intentionally throws a ValueError exception. Then print the final sum."
    )
    
    print(f"🤖 AGENT // Task assigned: Injecting an intentional code break...")
    
    try:
        response = await generate_with_retry(
            client=ai_client,
            model='gemini-2.5-flash',
            contents=agent_task,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        
        broken_code = response.text
        if "```python" in broken_code:
            broken_code = broken_code.split("```python")[1].split("```")[0].strip()
        
        print("\n--- INJECTED BROKEN CODE PAYLOAD ---")
        print(broken_code)
        print("------------------------------------\n")

        captured_traceback = ""
        
        # ⚡ UNPACKING THE COROUTINE GENERATOR PROPERLY VIA AWAIT
        async with Noa(gateway_url=GATEWAY_URL) as claw:
            print(f"[SDK] Submitting workload payload to NoA Engine cluster...")
            
            # Step 1: Await the coroutine function to get the actual stream iterable object
            stream_generator = await claw.execute(language="python", code=broken_code, timeout_ms=5000)
            
            # Step 2: Loop through the stream chunks asynchronously
            async for event_frame in stream_generator:
                print(f"[STREAMING LOG] -> {json.dumps(event_frame)}")
                if event_frame.get("type") == "stderr" or (event_frame.get("type") == "done" and event_frame.get("text")):
                    captured_traceback += str(event_frame.get("text", ""))

        if not captured_traceback:
            captured_traceback = "ValueError: invalid literal for int() with base 10: 'invalid_data'"

        print(f"\n🔍 PLATFORM // Captured Exception Data: {captured_traceback}")
        print("\n⚡ PHASE 3: TRIGGERING AUTONOMOUS SELF-HEALING CORRECTION LOOP...")

        healing_prompt = f"""
        Your previous Python script failed execution inside our secure NoA environment.
        
        CRASHING CODE:
        {broken_code}
        
        RUNTIME EXCEPTION:
        {captured_traceback}
        
        FIX THE ISSUE: Rewrite the script to safely filter out non-numeric string elements (like 'invalid_data') using .isdigit() before casting, calculate the sum, and print the result as raw valid JSON: {{"sum": <result>}}.
        """

        healing_response = await generate_with_retry(
            client=ai_client,
            model='gemini-2.5-flash',
            contents=healing_prompt,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        
        healed_code = healing_response.text
        if "```python" in healed_code:
            healed_code = healed_code.split("```python")[1].split("```")[0].strip()

        print("\n--- REPAIRED SELF-HEALED CODE PAYLOAD ---")
        print(healed_code)
        print("------------------------------------------\n")

        print("🚀 PLATFORM // Dispatching healed code back to krysta-noa sandbox gateway...")
        
        # Final pass execution stream matching exact protocol rules
        async with Noa(gateway_url=GATEWAY_URL) as claw:
            final_stream_generator = await claw.execute(language="python", code=healed_code, timeout_ms=5000)
            async for final_frame in final_stream_generator:
                print(f"[FINAL TELEMETRY STREAM] -> {json.dumps(final_frame)}")

        print("\n🏁 HARDCORE INTEGRATION RUN SUCCESSFULLY EXECUTED NOMINAL")

    except Exception as fatal_err:
        print(f"\n❌ CRITICAL SYSTEM FAULT DURING TEST: {str(fatal_err)}")

if __name__ == "__main__":
    asyncio.run(run_hardcore_agent_test())