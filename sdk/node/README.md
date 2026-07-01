# hoare-agent Node.js SDK

Formally-verified code pipeline — Node.js SDK.

```bash
npm install hoare-agent
```

## `verify()` function

```javascript
const { verify } = require('hoare-agent');

const result = await verify({
  precondition:  'n >= 0',
  postcondition: 'n >= 0',
  program:       'def transform(data): return data',
}, {
  backendUrl: 'http://localhost:8080',
});

if (result.verified) {
  console.log(`✓ Verified in ${result.elapsed_ms} ms`);
} else if (result.verdict === 'COUNTEREXAMPLE') {
  console.error(`✗ Counterexample: ${result.counterexample}`);
} else {
  console.error(`✗ ${result.verdict}: ${result.error_detail}`);
}
```

### TypeScript

```typescript
import { verify, HoareTriple, VerificationResult } from 'hoare-agent';

const triple: HoareTriple = {
  precondition:  'n >= 0',
  postcondition: 'n >= 0',
};

const result: VerificationResult = await verify(triple, {
  backendUrl: 'http://localhost:8080',
});
```

## Environment variable

Set `HOARE_BACKEND_URL` to avoid passing `backendUrl` in every call:

```bash
export HOARE_BACKEND_URL=http://localhost:8080
```

## API reference

### `verify(triple, options?)`

| Parameter             | Type       | Description |
|-----------------------|------------|-------------|
| `triple.precondition` | `string`   | Pre-condition P |
| `triple.postcondition`| `string`   | Post-condition Q |
| `triple.program`      | `string?`  | Optional program text |
| `triple.loop_invariants` | `string[]?` | Optional loop invariants |
| `options.backendUrl`  | `string?`  | Backend URL (default: `http://localhost:8080`) |
| `options.timeoutMs`   | `number?`  | HTTP timeout in ms (default: `10000`) |

Returns `Promise<VerificationResult>`:

| Field           | Type      | Description |
|-----------------|-----------|-------------|
| `verified`      | `boolean` | True iff formally proved |
| `verdict`       | `string`  | `VERIFIED` \| `COUNTEREXAMPLE` \| `TIMEOUT` \| `ERROR` |
| `counterexample`| `string`  | Counter-example (when `COUNTEREXAMPLE`) |
| `error_detail`  | `string`  | Error message (when `ERROR` or `TIMEOUT`) |
| `elapsed_ms`    | `number`  | Solver time in milliseconds |
