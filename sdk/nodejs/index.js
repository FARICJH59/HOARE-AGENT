/**
 * hoare-agent Node.js SDK
 * ========================
 * Formally verify code triples {pre} code {post} via the HOARE-AGENT HTTP API.
 *
 * @module hoare-agent
 */

"use strict";

const DEFAULT_BACKEND_URL = process.env.HOARE_BACKEND_URL || "http://localhost:8080";

// ---------------------------------------------------------------------------
// Result class
// ---------------------------------------------------------------------------

/**
 * Result of a Hoare triple verification.
 */
class HoareResult {
  /**
   * @param {object} data
   * @param {boolean} data.verified
   * @param {string}  data.verdict
   * @param {string}  [data.counterexample]
   * @param {string}  [data.error_detail]
   * @param {number}  [data.elapsed_ms]
   */
  constructor(data) {
    /** @type {boolean} True when the triple was formally proved. */
    this.verified = Boolean(data.verified);
    /** @type {string} "VERIFIED" | "COUNTEREXAMPLE" | "TIMEOUT" | "ERROR" */
    this.verdict = data.verdict || "ERROR";
    /** @type {string} Counter-example witness (if any). */
    this.counterexample = data.counterexample || "";
    /** @type {string} Error / timeout message (if any). */
    this.errorDetail = data.error_detail || "";
    /** @type {number} Solver wall time in milliseconds. */
    this.elapsedMs = data.elapsed_ms || 0;
  }

  toString() {
    const icon = this.verified ? "✓" : "✗";
    const suffix = this.counterexample ? `: ${this.counterexample}` : "";
    return `${icon} ${this.verdict}${suffix}`;
  }
}

// ---------------------------------------------------------------------------
// Internal HTTP helper
// ---------------------------------------------------------------------------

/**
 * POST JSON to a URL and return the parsed response body.
 * Works with Node's built-in `fetch` (Node ≥ 18) or falls back to `http`.
 *
 * @param {string} url
 * @param {object} body
 * @returns {Promise<object>}
 */
async function _post(url, body) {
  const payload = JSON.stringify(body);

  // Use native fetch when available (Node ≥ 18)
  if (typeof fetch !== "undefined") {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`HTTP ${res.status}: ${text}`);
    }
    return res.json();
  }

  // Fallback: Node http/https built-in modules
  const { request } = url.startsWith("https") ? require("https") : require("http");
  return new Promise((resolve, reject) => {
    const parsedUrl = new URL(url);
    const options = {
      hostname: parsedUrl.hostname,
      port: parsedUrl.port || (parsedUrl.protocol === "https:" ? 443 : 80),
      path: parsedUrl.pathname + parsedUrl.search,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(payload),
      },
    };
    const req = request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => { data += chunk; });
      res.on("end", () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(new Error(`Failed to parse response: ${data}`));
        }
      });
    });
    req.on("error", reject);
    req.write(payload);
    req.end();
  });
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Verify a Hoare triple `{pre} code {post}` using the HOARE-AGENT backend.
 *
 * @param {object}  options
 * @param {string}  [options.code]        Source code / program string (informational).
 * @param {string}  [options.pre="True"]  Pre-condition expression.
 * @param {string}  [options.post="True"] Post-condition expression.
 * @param {string[]} [options.loopInvariants=[]] Loop invariant expressions.
 * @param {number}  [options.timeoutMs=5000]  Solver timeout in milliseconds.
 * @param {string}  [options.backendUrl]  Override the backend URL.
 * @returns {Promise<HoareResult>}
 *
 * @example
 * const { verify } = require("hoare-agent");
 * const result = await verify({ pre: "x >= 0", post: "x >= 0" });
 * console.log(result.verified); // true
 */
async function verify({
  code = "",
  pre = "True",
  post = "True",
  loopInvariants = [],
  timeoutMs = 5_000,
  backendUrl = DEFAULT_BACKEND_URL,
} = {}) {
  const body = {
    triple: {
      precondition: pre,
      program: typeof code === "function" ? code.toString() : String(code),
      postcondition: post,
      loop_invariants: loopInvariants,
    },
    timeout_ms: timeoutMs,
  };

  try {
    const data = await _post(`${backendUrl}/verify`, body);
    return new HoareResult(data);
  } catch (err) {
    return new HoareResult({
      verified: false,
      verdict: "ERROR",
      error_detail: err.message,
    });
  }
}

/**
 * Wraps an async function and verifies its Hoare triple before first call.
 * Stores the result on `fn.hoareResult`.
 *
 * @param {object}   options
 * @param {string}   [options.pre="True"]
 * @param {string}   [options.post="True"]
 * @param {string[]} [options.loopInvariants=[]]
 * @param {number}   [options.timeoutMs=5000]
 * @param {string}   [options.backendUrl]
 * @param {boolean}  [options.raiseOnFailure=false]
 * @returns {(fn: Function) => Function}
 *
 * @example
 * const { verified } = require("hoare-agent");
 *
 * const double = verified({ pre: "x >= 0", post: "result >= 0" })(
 *   async (x) => x * 2
 * );
 * await double.verificationReady;
 */
function verified({
  pre = "True",
  post = "True",
  loopInvariants = [],
  timeoutMs = 5_000,
  backendUrl = DEFAULT_BACKEND_URL,
  raiseOnFailure = false,
} = {}) {
  return function decorator(fn) {
    const resultPromise = verify({ pre, post, loopInvariants, timeoutMs, backendUrl });

    async function wrapper(...args) {
      return fn(...args);
    }

    // Expose the promise so callers can await it
    wrapper.verificationReady = resultPromise.then((result) => {
      wrapper.hoareResult = result;
      if (raiseOnFailure && !result.verified) {
        throw new Error(
          `Hoare verification failed for ${fn.name || "anonymous"}: ${result}`
        );
      }
      return result;
    });

    return wrapper;
  };
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

module.exports = { verify, verified, HoareResult };
