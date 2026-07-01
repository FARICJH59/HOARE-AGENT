// hoare-agent TypeScript type definitions

export interface VerifyOptions {
  /** Source code / program string (informational). */
  code?: string | Function;
  /** Pre-condition expression. Default: "True". */
  pre?: string;
  /** Post-condition expression. Default: "True". */
  post?: string;
  /** Optional loop invariant expressions. */
  loopInvariants?: string[];
  /** Solver timeout in milliseconds. Default: 5000. */
  timeoutMs?: number;
  /** Override the backend URL. Default: process.env.HOARE_BACKEND_URL or "http://localhost:8080". */
  backendUrl?: string;
}

export interface VerifiedOptions extends VerifyOptions {
  /** Throw an Error when verification fails. Default: false. */
  raiseOnFailure?: boolean;
}

/** Result of a Hoare triple verification. */
export declare class HoareResult {
  /** True when the triple was formally proved. */
  readonly verified: boolean;
  /** "VERIFIED" | "COUNTEREXAMPLE" | "TIMEOUT" | "ERROR" */
  readonly verdict: "VERIFIED" | "COUNTEREXAMPLE" | "TIMEOUT" | "ERROR";
  /** Counter-example witness (if any). */
  readonly counterexample: string;
  /** Error / timeout message (if any). */
  readonly errorDetail: string;
  /** Solver wall time in milliseconds. */
  readonly elapsedMs: number;
  toString(): string;
}

/**
 * Verify a Hoare triple `{pre} code {post}` using the HOARE-AGENT backend.
 *
 * @example
 * const result = await verify({ pre: "x >= 0", post: "x >= 0" });
 */
export declare function verify(options?: VerifyOptions): Promise<HoareResult>;

/**
 * Decorator factory — verifies the triple at decoration time.
 * Stores the result promise on `fn.verificationReady`.
 *
 * @example
 * const double = verified({ pre: "x >= 0", post: "result >= 0" })(
 *   async (x) => x * 2
 * );
 * await double.verificationReady;
 */
export declare function verified(options?: VerifiedOptions): (fn: Function) => Function;
