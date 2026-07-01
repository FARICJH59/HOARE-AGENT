/**
 * hoare-agent Node.js SDK
 *
 * Delegates verification to a running Hoare-Agent backend REST API.
 *
 * @example
 * const { verify } = require('hoare-agent');
 *
 * const result = await verify({
 *   precondition:  'n >= 0',
 *   postcondition: 'n >= 0',
 *   program:       'def transform(data): return data',
 * }, { backendUrl: 'http://localhost:8080' });
 *
 * if (result.verified) {
 *   console.log('✓ Verified in', result.elapsed_ms, 'ms');
 * } else {
 *   console.error('✗', result.verdict, result.counterexample || result.error_detail);
 * }
 */

'use strict';

const https = require('https');
const http  = require('http');

const DEFAULT_BACKEND_URL = process.env.HOARE_BACKEND_URL || 'http://localhost:8080';
const DEFAULT_TIMEOUT_MS  = 10_000;

/**
 * @typedef {Object} HoareTriple
 * @property {string}   precondition    - Pre-condition P expression
 * @property {string}   postcondition   - Post-condition Q expression
 * @property {string}   [program]       - Optional program text C
 * @property {string[]} [loop_invariants] - Optional loop invariant expressions
 */

/**
 * @typedef {Object} VerificationResult
 * @property {boolean} verified         - True iff the triple was formally proved
 * @property {string}  verdict          - "VERIFIED" | "COUNTEREXAMPLE" | "TIMEOUT" | "ERROR"
 * @property {string}  [counterexample] - Counter-example assignment (when verdict is COUNTEREXAMPLE)
 * @property {string}  [error_detail]   - Error message (when verdict is ERROR or TIMEOUT)
 * @property {number}  elapsed_ms       - Solver time in milliseconds
 */

/**
 * @typedef {Object} VerifyOptions
 * @property {string} [backendUrl]  - Base URL of the Hoare-Agent backend (default: http://localhost:8080)
 * @property {number} [timeoutMs]  - HTTP request timeout in milliseconds (default: 10 000)
 */

/**
 * Verify a Hoare triple via the Hoare-Agent backend REST API.
 *
 * @param {HoareTriple} triple      - The Hoare triple to verify
 * @param {VerifyOptions} [options] - Optional configuration
 * @returns {Promise<VerificationResult>}
 */
async function verify(triple, options = {}) {
  const backendUrl = (options.backendUrl || DEFAULT_BACKEND_URL).replace(/\/$/, '');
  const timeoutMs  = options.timeoutMs || DEFAULT_TIMEOUT_MS;
  const url        = `${backendUrl}/verify`;

  const body = JSON.stringify({
    triple: {
      precondition:    triple.precondition,
      postcondition:   triple.postcondition,
      program:         triple.program         || '',
      loop_invariants: triple.loop_invariants || [],
    },
  });

  return _post(url, body, timeoutMs);
}

/**
 * Send a POST request and return the parsed JSON response body.
 *
 * @param {string} url
 * @param {string} body
 * @param {number} timeoutMs
 * @returns {Promise<VerificationResult>}
 */
function _post(url, body, timeoutMs) {
  return new Promise((resolve) => {
    const parsed  = new URL(url);
    const driver  = parsed.protocol === 'https:' ? https : http;
    const options = {
      hostname: parsed.hostname,
      port:     parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
      path:     parsed.pathname + (parsed.search || ''),
      method:   'POST',
      headers: {
        'Content-Type':   'application/json',
        'Content-Length': Buffer.byteLength(body),
      },
      timeout: timeoutMs,
    };

    const req = driver.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          resolve({
            verified:       json.verified       ?? false,
            verdict:        json.verdict        ?? 'ERROR',
            counterexample: json.counterexample ?? '',
            error_detail:   json.error_detail   ?? '',
            elapsed_ms:     json.elapsed_ms     ?? 0,
          });
        } catch (_) {
          resolve({
            verified:     false,
            verdict:      'ERROR',
            error_detail: `Invalid JSON response from backend: ${data.slice(0, 200)}`,
            elapsed_ms:   0,
          });
        }
      });
    });

    req.on('timeout', () => {
      req.destroy();
      resolve({
        verified:     false,
        verdict:      'TIMEOUT',
        error_detail: `Request to ${url} timed out after ${timeoutMs} ms`,
        elapsed_ms:   timeoutMs,
      });
    });

    req.on('error', (err) => {
      resolve({
        verified:     false,
        verdict:      'ERROR',
        error_detail: `Cannot reach backend at ${url}: ${err.message}`,
        elapsed_ms:   0,
      });
    });

    req.write(body);
    req.end();
  });
}

module.exports = { verify };
