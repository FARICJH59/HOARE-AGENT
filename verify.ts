// HOARE-AGENT/verify.ts
// Central verification engine for all HOARE agents

export function verify(result: any) {
  let safe = true;

  // Carbon Agent Verification
  if (result.agent === "carbon") {
    safe = result.output?.complianceCheck?.score >= 60;
  }

  // Energy Agent Verification
  if (result.agent === "energy") {
    safe = result.output?.facilityScore >= 60;
  }

  return {
    safe,
    agent: result.agent,
    reason: safe ? "Verified" : "Verification failed",
    timestamp: Date.now()
  };
}
