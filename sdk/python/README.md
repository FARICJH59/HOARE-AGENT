# hoare-agent Python SDK

> **Formally verify Python functions with one line of code.**

```bash
pip install hoare-agent
```

## Quick start

```python
from hoareagent import verify

def add_positive(x, y):
    """
    :pre:  x >= 0 and y >= 0
    :post: result >= 0
    """
    return x + y

result = verify(code=add_positive)
print(result)   # ✓ VERIFIED
```

## Explicit conditions

```python
result = verify(
    code=add_positive,
    pre="x >= 0 and y >= 0",
    post="result >= 0",
)
assert result.verified
```

## Decorator

```python
from hoareagent import verified

@verified(pre="x >= 0", post="result >= 0")
def double(x):
    return x * 2

print(double.hoare_result)   # ✓ VERIFIED
```

## CLI

```bash
# Verify all annotated functions in a file
hoare-agent verify mymodule.py

# Pass conditions explicitly
hoare-agent verify mymodule.py --pre "x >= 0" --post "result >= 0"
```

## Annotating functions

Add `:pre:` / `:post:` fields to any docstring:

```python
def clamp(value, lo, hi):
    """
    :pre:  lo <= hi
    :post: result >= lo and result <= hi
    """
    return max(lo, min(hi, value))
```

Or use comment-style annotations directly above the `def`:

```python
# pre:  n > 0
# post: result >= 0
def square_root_approx(n):
    ...
```

## API reference

### `verify(code, *, pre=None, post=None, loop_invariants=None, timeout_ms=5000)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `code` | callable or str | Function or source to verify |
| `pre` | str | Pre-condition expression (extracted from docstring if omitted) |
| `post` | str | Post-condition expression (extracted from docstring if omitted) |
| `loop_invariants` | list[str] | Optional loop invariants |
| `timeout_ms` | int | Z3 solver timeout (ms) |

Returns a `HoareResult` with attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `verified` | bool | `True` when proved |
| `verdict` | str | `"VERIFIED"`, `"COUNTEREXAMPLE"`, `"TIMEOUT"`, `"ERROR"` |
| `counterexample` | str | Counter-example witness (if any) |
| `error_detail` | str | Error message (if any) |
| `elapsed_ms` | int | Solver wall time |

### `@verified(*, pre, post, ...)`

Class decorator that calls `verify()` at import time and stores the result
on `fn.hoare_result`.  Pass `raise_on_failure=True` to turn failures into
`AssertionError`.

## Requirements

- Python ≥ 3.9
- [`z3-solver`](https://pypi.org/project/z3-solver/) ≥ 4.13
