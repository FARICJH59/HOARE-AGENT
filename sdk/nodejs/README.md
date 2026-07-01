# hoare-agent Node.js SDK

> **Formally verify code with one line of JavaScript.**

```bash
npm install hoare-agent
```

> **Prerequisites:** a running HOARE-AGENT backend (default `http://localhost:8080`).
> Set the `HOARE_BACKEND_URL` environment variable to override.

## Quick start

```js
const { verify } = require("hoare-agent");

const result = await verify({
  pre:  "x >= 0 and y >= 0",
  post: "result >= 0",
});
console.log(result.toString()); // ✓ VERIFIED
console.log(result.verified);   // true
```

## ESM / TypeScript

```ts
import { verify, HoareResult } from "hoare-agent";

const result: HoareResult = await verify({
  pre:  "n > 5",
  post: "n > 0",
});
```

## `verified` decorator helper

```js
const { verified } = require("hoare-agent");

const double = verified({ pre: "x >= 0", post: "result >= 0" })(
  async (x) => x * 2
);

// Wait for verification to complete
const verResult = await double.verificationReady;
console.log(verResult.verified); // true
```

## API

### `verify(options?) → Promise<HoareResult>`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `code` | string \| Function | `""` | Source code (informational) |
| `pre` | string | `"True"` | Pre-condition expression |
| `post` | string | `"True"` | Post-condition expression |
| `loopInvariants` | string[] | `[]` | Loop invariants |
| `timeoutMs` | number | `5000` | Solver timeout (ms) |
| `backendUrl` | string | env / `localhost:8080` | Backend endpoint |

### `HoareResult`

| Property | Type | Description |
|----------|------|-------------|
| `verified` | boolean | `true` when proved |
| `verdict` | string | `"VERIFIED"` / `"COUNTEREXAMPLE"` / `"TIMEOUT"` / `"ERROR"` |
| `counterexample` | string | Counter-example (if any) |
| `errorDetail` | string | Error message (if any) |
| `elapsedMs` | number | Solver wall time |

### `verified(options?) → (fn) → fn`

Decorator factory; attaches `.hoarResult` and `.verificationReady` (Promise)
to the wrapped function.  Set `raiseOnFailure: true` to throw on failure.

## Environment variables

| Variable | Description |
|----------|-------------|
| `HOARE_BACKEND_URL` | Backend base URL (default: `http://localhost:8080`) |
