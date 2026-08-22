export type AdapterOperation = 'inspect' | 'plan' | 'build' | 'test' | 'deploy' | 'rollback';

export interface AdapterContext {
  tenantId?: string;
  correlationId?: string;
  repository?: string;
  projectRoot?: string;
  environment?: string;
  dryRun?: boolean;
}

export interface AdapterCapability {
  operation: AdapterOperation;
  supported: boolean;
  reason?: string;
}

export interface AdapterPlan {
  adapterId: string;
  operation: AdapterOperation;
  commands: string[];
  files?: string[];
  requiresExternalRuntime: boolean;
  approvalRequired: boolean;
}

export interface AdapterResult {
  ok: boolean;
  adapterId: string;
  operation: AdapterOperation;
  message: string;
  metadata?: Record<string, unknown>;
}

/** Provider-neutral execution boundary. Adapters must never bypass HOARE policy. */
export interface TargetAdapter {
  readonly id: string;
  readonly version: string;
  capabilities(context: AdapterContext): Promise<AdapterCapability[]>;
  inspect(context: AdapterContext): Promise<AdapterResult>;
  plan(context: AdapterContext): Promise<AdapterPlan>;
  build(context: AdapterContext, plan: AdapterPlan): Promise<AdapterResult>;
  test(context: AdapterContext, plan: AdapterPlan): Promise<AdapterResult>;
  deploy(context: AdapterContext, plan: AdapterPlan): Promise<AdapterResult>;
  rollback?(context: AdapterContext, plan: AdapterPlan): Promise<AdapterResult>;
}
