# NoA Python SDK API Reference Documentation

This document provides technical reference details for the classes, methods, parameters, and streaming response objects available within the `krysta` client library.

---

## Core Class Architecture

### `NoA` Class
The main client manager used to initialize connections and manage state lifecycle pipes with your remote execution infrastructure gateway.

```python
from krysta.noa import Noa
```

#### Class Constructor Matrix
```python
Noa(gateway_url: str)
```
* **Parameters:**
  * `gateway_url` *(str, Required)*: The base HTTP/WS network address of your running NoA server cluster dashboard node (e.g., `"http://localhost:3000"`).

#### Context Manager Methods
The client class fully implements the standard asynchronous context manager layout (`__aenter__` / `__aexit__`) to automatically handle socket connections, channel allocations, and memory resource cleanups safely.

```python
async with Noa(gateway_url="...") as client:
    # Execution resources are automatically allocated here
    pass
# Connection pipes are safely destroyed here
```

---

## Method Reference Maps

### `execute()`
Initiates an asynchronous Server-Sent Events (SSE) background task worker thread to evaluate a raw source code string.

#### Method Definition Syntax
```python
def execute(
    language: str, 
    code: str, 
    timeout_ms: int = 5000
) -> AsyncIterator[dict]:
```

#### Input Arguments Block
* **`language`** *(str, Required)*: The programming compilation runner target environment to spawn inside the isolated cluster node. Supported strings:
  * `"python"`
  * `"javascript"`
* **`code`** *(str, Required)*: The uncompiled text string payload containing the raw source code script to evaluate inside the container pool.
* **`timeout_ms`** *(int, Optional)*: The strict maximum allowed execution time window in milliseconds before the watchdog thread hard-kills (`SIGKILL`) the task runner. Default fallback threshold value: `5000`.

#### Return Type Value
* Returns an **`AsyncIterator[dict]`** stream generator object. You must consume this data payload frame-by-frame using an `async for` loop layout block.

---

## Stream Event Response Payload Schema

Every data unit emitted from the async iterator returns a structured Python `dict` map object containing the following token parameters:

```json
{
  "type": "system" | "stdout" | "stderr" | "rules" | "done" | "error",
  "text": string | null,
  "timestamp": integer
}
```

### Event Parameter Types Definition Matrix

#### 1. `type: "system"`
Emitted immediately when the gateway server begins allocating memory allocations or scheduling task execution queues.
* **Text Contents:** Standard tracking message flags (e.g., `"EXECUTION_STARTED"`).

#### 2. `type: "stdout"`
Emitted instantly whenever the sandboxed script writes characters to the standard console system output.
* **Text Contents:** The raw printed string text data.

#### 3. `type: "stderr"`
Emitted instantly when unhandled runtime errors, system exceptions, or line code tracebacks occur inside the isolated runner.
* **Text Contents:** Standard multiline traceback exception information text.

#### 4. `type: "rules"`
Emitted near task termination. Contains a serialized JSON string listing static metric quality scores and evaluation check markers.
* **Text Contents Schema:**
  ```json
  "[{\"rule\": \"ExitCodeZeroRule\", \"result\": \"PASS\" | \"FAIL\", \"reason\": \"...\"}]"
  ```

#### 5. `type: "done"`
Emitted when the execution lifecycle pipeline completes its loop naturally and closes down successfully.
* **Text Contents:** `null`

#### 6. `type: "error"`
Emitted if a network drop occurs, or if the server cannot complete an internal spawn routing operation.
* **Text Contents:** Detailed platform failure tracking notes (e.g., `"Job failed during execution"`).
