# HOARE-AGENT Verify Action

> Formally verify Python functions annotated with Hoare logic in your CI/CD pipeline.

```yaml
- uses: FARICJH59/HOARE-AGENT/action@v1
```

## Usage

### Basic — verify all annotated functions

```yaml
steps:
  - uses: actions/checkout@v4

  - name: Hoare verification
    uses: FARICJH59/HOARE-AGENT/action@v1
    with:
      path: "src/**/*.py"
```

Functions annotated with `:pre:` / `:post:` docstring fields are verified
automatically:

```python
def clamp(value, lo, hi):
    """
    :pre:  lo <= hi
    :post: result >= lo and result <= hi
    """
    return max(lo, min(hi, value))
```

### Explicit conditions

```yaml
- uses: FARICJH59/HOARE-AGENT/action@v1
  with:
    path: "mymodule.py"
    pre:  "x >= 0 and y >= 0"
    post: "result >= 0"
```

### Full example

```yaml
name: Formal Verification

on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Hoare verification
        id: hoare
        uses: FARICJH59/HOARE-AGENT/action@v1
        with:
          path:           "src/**/*.py"
          timeout_ms:     "10000"
          python_version: "3.11"

      - name: Print summary
        run: echo "${{ steps.hoare.outputs.summary }}"
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `path` | No | `**/*.py` | Glob pattern(s) for files to verify |
| `pre` | No | _(from docstring)_ | Override pre-condition |
| `post` | No | _(from docstring)_ | Override post-condition |
| `timeout_ms` | No | `5000` | Z3 solver timeout per triple (ms) |
| `python_version` | No | `3.11` | Python version to use |
| `fail_on_error` | No | `true` | Fail step when any triple fails |
| `sdk_ref` | No | _(current SHA)_ | SDK git ref to install |

## Outputs

| Output | Description |
|--------|-------------|
| `verified` | `"true"` when all triples passed |
| `summary` | Human-readable summary line |

The action also writes a full Markdown table to the GitHub Step Summary.

## Annotation format

### Docstring (recommended)

```python
def add(x, y):
    """
    :pre:  x >= 0 and y >= 0
    :post: result >= 0
    """
    return x + y
```

### Comment block above `def`

```python
# pre:  n > 0
# post: result >= 1
def factorial(n):
    ...
```

## Requirements

- A GitHub-hosted runner (ubuntu, macos, or windows)
- Python ≥ 3.9 (installed automatically by the action)
