import type { AdapterCapability, AdapterContext, AdapterPlan, AdapterResult, TargetAdapter } from '../TargetAdapter';

/**
 * Provider boundary only. Credentials and production API calls are intentionally
 * not embedded in the core adapter. A production implementation must use a
 * secret-backed provider client and pass HOARE policy/approval gates first.
 */
export class VercelProductionAdapter implements TargetAdapter {
  readonly id = 'vercel-prod';
  readonly version = '0.1.0';

  async capabilities(_context: AdapterContext): Promise<AdapterCapability[]> {
    return [
      { operation: 'inspect', supported: true },
      { operation: 'plan', supported: true },
      { operation: 'build', supported: false, reason: 'Build execution is delegated to the configured build worker.' },
      { operation: 'test', supported: false, reason: 'Tests run in the selected build worker before deployment.' },
      { operation: 'deploy', supported: true, reason: 'Requires authenticated Vercel provider credentials.' },
      { operation: 'rollback', supported: true, reason: 'Requires authenticated Vercel provider credentials.' },
    ];
  }

  async inspect(_context: AdapterContext): Promise<AdapterResult> {
    return { ok: true, adapterId: this.id, operation: 'inspect', message: 'Vercel production target adapter registered.' };
  }

  async plan(context: AdapterContext): Promise<AdapterPlan> {
    return {
      adapterId: this.id,
      operation: 'deploy',
      commands: ['validate deployment target', 'verify build artifact', 'authorize deployment', 'deploy via provider client'],
      files: context.projectRoot ? [context.projectRoot] : undefined,
      requiresExternalRuntime: true,
      approvalRequired: true,
    };
  }

  async build(_context: AdapterContext, _plan: AdapterPlan): Promise<AdapterResult> {
    return { ok: false, adapterId: this.id, operation: 'build', message: 'Vercel adapter does not own the build worker.' };
  }

  async test(_context: AdapterContext, _plan: AdapterPlan): Promise<AdapterResult> {
    return { ok: false, adapterId: this.id, operation: 'test', message: 'Tests must pass before this deployment adapter is invoked.' };
  }

  async deploy(context: AdapterContext, plan: AdapterPlan): Promise<AdapterResult> {
    if (context.dryRun || plan.requiresExternalRuntime) {
      return { ok: true, adapterId: this.id, operation: 'deploy', message: 'Deployment plan prepared; provider execution requires authenticated external runtime.' };
    }
    return { ok: false, adapterId: this.id, operation: 'deploy', message: 'Provider execution client is not configured.' };
  }

  async rollback(_context: AdapterContext, _plan: AdapterPlan): Promise<AdapterResult> {
    return { ok: false, adapterId: this.id, operation: 'rollback', message: 'Rollback requires the authenticated provider execution client.' };
  }
}
