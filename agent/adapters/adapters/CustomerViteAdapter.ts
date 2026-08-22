import type { AdapterCapability, AdapterContext, AdapterPlan, AdapterResult, TargetAdapter } from '../TargetAdapter';

/** Provider-neutral customer-managed Vite build/deploy target. */
export class CustomerViteAdapter implements TargetAdapter {
  readonly id = 'customer-vite';
  readonly version = '0.1.0';

  async capabilities(_context: AdapterContext): Promise<AdapterCapability[]> {
    return [
      { operation: 'inspect', supported: true },
      { operation: 'plan', supported: true },
      { operation: 'build', supported: true },
      { operation: 'test', supported: true },
      { operation: 'deploy', supported: true, reason: 'Customer runtime must expose an approved deployment endpoint or worker.' },
      { operation: 'rollback', supported: true, reason: 'Customer runtime must provide a rollback contract.' },
    ];
  }

  async inspect(_context: AdapterContext): Promise<AdapterResult> {
    return { ok: true, adapterId: this.id, operation: 'inspect', message: 'Customer Vite builder target registered.' };
  }

  async plan(context: AdapterContext): Promise<AdapterPlan> {
    return {
      adapterId: this.id,
      operation: 'build',
      commands: ['detect Vite project', 'install locked dependencies', 'npm run build', 'run configured tests'],
      files: context.projectRoot ? [context.projectRoot] : undefined,
      requiresExternalRuntime: false,
      approvalRequired: false,
    };
  }

  async build(_context: AdapterContext, _plan: AdapterPlan): Promise<AdapterResult> {
    return { ok: true, adapterId: this.id, operation: 'build', message: 'Customer Vite build plan is ready for the selected worker.' };
  }

  async test(_context: AdapterContext, _plan: AdapterPlan): Promise<AdapterResult> {
    return { ok: true, adapterId: this.id, operation: 'test', message: 'Customer Vite tests are delegated to the selected worker.' };
  }

  async deploy(_context: AdapterContext, _plan: AdapterPlan): Promise<AdapterResult> {
    return { ok: false, adapterId: this.id, operation: 'deploy', message: 'Customer deployment endpoint is not configured.' };
  }

  async rollback(_context: AdapterContext, _plan: AdapterPlan): Promise<AdapterResult> {
    return { ok: false, adapterId: this.id, operation: 'rollback', message: 'Customer rollback endpoint is not configured.' };
  }
}
