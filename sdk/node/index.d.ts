export interface HoareTriple {
  precondition:     string;
  postcondition:    string;
  program?:         string;
  loop_invariants?: string[];
}

export type VerificationVerdict =
  | 'VERIFIED'
  | 'COUNTEREXAMPLE'
  | 'TIMEOUT'
  | 'ERROR';

export interface VerificationResult {
  verified:       boolean;
  verdict:        VerificationVerdict;
  counterexample?: string;
  error_detail?:  string;
  elapsed_ms:     number;
}

export interface VerifyOptions {
  /** Base URL of the Hoare-Agent backend (default: http://localhost:8080) */
  backendUrl?: string;
  /** HTTP request timeout in milliseconds (default: 10 000) */
  timeoutMs?: number;
}

/**
 * Verify a Hoare triple via the Hoare-Agent backend REST API.
 */
export function verify(triple: HoareTriple, options?: VerifyOptions): Promise<VerificationResult>;
