# hoare-agent Python SDK

Formally-verified code pipeline — Python SDK and CLI.

```bash
pip install hoare-agent
```

## `verify()` function

```python
from hoare_agent import verify

result = verify(
    precondition="n >= 0",
    postcondition="n >= 0",
    program="def transform(data): return data",
)

if result:
    print(f"✓ Verified in {result.elapsed_ms} ms")
else:
    print(f"✗ {result}")
```

### With loop invariants

```python
result = verify(
    precondition="n >= 0 and i == 0",
    postcondition="i == n",
    loop_invariants=["i >= 0 and i <= n"],
)
```

### Against a running backend

```python
result = verify(
    precondition="n >= 0",
    postcondition="n >= 0",
    backend_url="http://localhost:8080",
)
```

## CLI

```bash
# Verify a file with inline annotations
hoare-agent verify mymodule.py

# Verify with explicit conditions
hoare-agent verify --pre "n >= 0" --post "n >= 0" mymodule.py

# Verify a JSON triple file
hoare-agent verify triple.json

# Output JSON result (for CI)
hoare-agent verify --json mymodule.py

# Use backend REST API
hoare-agent verify --backend http://localhost:8080 mymodule.py
```

### Inline annotation format

Add `# @pre:` and `# @post:` comments anywhere in your Python file:

```python
# @pre:  n >= 0
# @post: result >= 0
# @inv:  i >= 0   (optional, repeatable)
def transform(data: dict) -> dict:
    ...
```

### JSON triple file format

```json
{
  "precondition":   "n >= 0",
  "program":        "def transform(data): return data",
  "postcondition":  "n >= 0",
  "loop_invariants": []
}
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0`  | Triple verified |
| `1`  | Usage error (bad arguments, file not found, missing annotations) |
| `2`  | Verification failed (counterexample or error) |
