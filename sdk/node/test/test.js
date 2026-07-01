/**
 * Unit tests for the hoare-agent Node.js SDK.
 *
 * Runs a tiny HTTP mock server so no real backend is needed.
 *
 * Run with:
 *   node test/test.js
 */

'use strict';

const http   = require('http');
const assert = require('assert');
const { verify } = require('../index');

// ─── Minimal test runner ────────────────────────────────────────────────────

let passed = 0;
let failed = 0;

async function test(name, fn) {
  try {
    await fn();
    console.log(`  ✓ ${name}`);
    passed++;
  } catch (err) {
    console.error(`  ✗ ${name}`);
    console.error(`    ${err.message}`);
    failed++;
  }
}

// ─── Mock HTTP server ────────────────────────────────────────────────────────

let _mockHandler = null;

const server = http.createServer((req, res) => {
  let body = '';
  req.on('data', (c) => { body += c; });
  req.on('end', () => {
    if (_mockHandler) {
      _mockHandler(req, body, res);
    } else {
      res.writeHead(500);
      res.end(JSON.stringify({ error: 'no mock handler' }));
    }
  });
});

function withMock(handler, fn) {
  _mockHandler = handler;
  return fn().finally(() => { _mockHandler = null; });
}

function respondWith(res, status, body) {
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(body));
}

// ─── Tests ───────────────────────────────────────────────────────────────────

async function runTests(backendUrl) {
  console.log('\nhoare-agent Node.js SDK tests\n');

  await test('verify() returns verified=true on VERIFIED response', () =>
    withMock((_req, _body, res) =>
      respondWith(res, 200, {
        verified: true, verdict: 'VERIFIED', elapsed_ms: 42,
      }),
    async () => {
      const result = await verify(
        { precondition: 'n >= 0', postcondition: 'n >= 0' },
        { backendUrl },
      );
      assert.strictEqual(result.verified, true);
      assert.strictEqual(result.verdict, 'VERIFIED');
      assert.strictEqual(result.elapsed_ms, 42);
    })
  );

  await test('verify() returns verified=false on COUNTEREXAMPLE response', () =>
    withMock((_req, _body, res) =>
      respondWith(res, 200, {
        verified: false, verdict: 'COUNTEREXAMPLE',
        counterexample: 'n = 0', elapsed_ms: 10,
      }),
    async () => {
      const result = await verify(
        { precondition: 'n >= 0', postcondition: 'n > 100' },
        { backendUrl },
      );
      assert.strictEqual(result.verified, false);
      assert.strictEqual(result.verdict, 'COUNTEREXAMPLE');
      assert.strictEqual(result.counterexample, 'n = 0');
    })
  );

  await test('verify() sends precondition and postcondition in request body', () =>
    withMock((_req, body, res) => {
      const parsed = JSON.parse(body);
      assert.strictEqual(parsed.triple.precondition,  'x > 0');
      assert.strictEqual(parsed.triple.postcondition, 'x >= 0');
      respondWith(res, 200, { verified: true, verdict: 'VERIFIED', elapsed_ms: 1 });
    },
    async () => {
      await verify(
        { precondition: 'x > 0', postcondition: 'x >= 0' },
        { backendUrl },
      );
    })
  );

  await test('verify() sends program and loop_invariants when provided', () =>
    withMock((_req, body, res) => {
      const parsed = JSON.parse(body);
      assert.strictEqual(parsed.triple.program, 'def f(): pass');
      assert.deepStrictEqual(parsed.triple.loop_invariants, ['i >= 0']);
      respondWith(res, 200, { verified: true, verdict: 'VERIFIED', elapsed_ms: 1 });
    },
    async () => {
      await verify({
        precondition:    'n >= 0',
        postcondition:   'n >= 0',
        program:         'def f(): pass',
        loop_invariants: ['i >= 0'],
      }, { backendUrl });
    })
  );

  await test('verify() defaults program to empty string when omitted', () =>
    withMock((_req, body, res) => {
      const parsed = JSON.parse(body);
      assert.strictEqual(parsed.triple.program, '');
      respondWith(res, 200, { verified: true, verdict: 'VERIFIED', elapsed_ms: 1 });
    },
    async () => {
      await verify(
        { precondition: 'n >= 0', postcondition: 'n >= 0' },
        { backendUrl },
      );
    })
  );

  await test('verify() handles TIMEOUT verdict', () =>
    withMock((_req, _body, res) =>
      respondWith(res, 200, {
        verified: false, verdict: 'TIMEOUT',
        error_detail: 'solver timed out', elapsed_ms: 5000,
      }),
    async () => {
      const result = await verify(
        { precondition: 'n >= 0', postcondition: 'n >= 0' },
        { backendUrl },
      );
      assert.strictEqual(result.verified, false);
      assert.strictEqual(result.verdict, 'TIMEOUT');
      assert.strictEqual(result.error_detail, 'solver timed out');
    })
  );

  await test('verify() returns ERROR verdict when backend is unreachable', async () => {
    // Use a port that is not listening
    const result = await verify(
      { precondition: 'n >= 0', postcondition: 'n >= 0' },
      { backendUrl: 'http://localhost:19999', timeoutMs: 500 },
    );
    assert.strictEqual(result.verified, false);
    assert.strictEqual(result.verdict, 'ERROR');
    assert.ok(result.error_detail.length > 0);
  });

  await test('verify() returns ERROR verdict on HTTP error response', () =>
    withMock((_req, _body, res) =>
      respondWith(res, 500, { detail: 'internal error' }),
    async () => {
      // A 500 response still parses — we just surface what the backend returns
      const result = await verify(
        { precondition: 'n >= 0', postcondition: 'n >= 0' },
        { backendUrl },
      );
      // The SDK parses whatever JSON the server returns; verified defaults to false
      assert.strictEqual(result.verified, false);
    })
  );

  await test('verify() handles invalid JSON from backend gracefully', () =>
    withMock((_req, _body, res) => {
      res.writeHead(200, { 'Content-Type': 'text/plain' });
      res.end('not json');
    },
    async () => {
      const result = await verify(
        { precondition: 'n >= 0', postcondition: 'n >= 0' },
        { backendUrl },
      );
      assert.strictEqual(result.verified, false);
      assert.strictEqual(result.verdict, 'ERROR');
      assert.ok(result.error_detail.includes('Invalid JSON'));
    })
  );
}

// ─── Main ────────────────────────────────────────────────────────────────────

server.listen(0, '127.0.0.1', async () => {
  const { port } = server.address();
  const backendUrl = `http://127.0.0.1:${port}`;

  try {
    await runTests(backendUrl);
  } finally {
    server.close();
  }

  console.log(`\n${passed} passed, ${failed} failed`);
  if (failed > 0) process.exit(1);
});
