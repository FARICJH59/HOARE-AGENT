import type { AdapterCapability, AdapterContext, AdapterPlan, AdapterResult, TargetAdapter } from '../TargetAdapter';

export class TermuxAdapter implements TargetAdapter {
  readonly id = 'termux-local';
  readonly version = '1.0.0';

  async capabilities(_context: AdapterContext): Promise<AdapterCapability[]> {
    return [
      { operation: 'inspect', supported: true },
      { operation: 'plan', supported: true },
      { operation: 'build', supported: true },
      { operation: 'test', supported: true },
      { operation: 'deploy', supported: false, reason: 'Termux is treated as a local worker, not a production deployment target.' },
      { operation: 'rollback', supported: false, reason: 'Production rollback belongs to the selected deployment adapter.' },
    ];
  }

  async inspect(_context: AdapterContext): Promise<AdapterResult> {
    return { ok: true, adapterId: this.id, operation: 'inspect', message: 'Termux worker available for local inspection.' };
  }

  async plan(context: AdapterContext): Promise<AdapterPlan> {
    return {
      adapterId: this.id,
      operation: 'build',
      commands: ['project inspection', 'dependency validation', 'build', 'test'],
      files: context.projectRoot ? [context.projectRoot] : undefined,
      requiresExternalRuntime: false,
      approvalRequired: false,
    };
  }

  async build(_context: AdapterContext, _plan: AdapterPlan): Promise<AdapterResult> {
    return { ok: true, adapterId: this.id, operation: 'build', message: 'Build delegated to the Termux execution worker.' };
  }

  async test(_context: AdapterContext, _plan: AdapterPlan): Promise<AdapterResult> {
    return { ok: true, adapterId: this.id, operation: 'test', message: 'Tests delegated to the Termux execution worker.' };
  }

  async deploy(_context: AdapterContext, _plan: AdapterPlan): Promise<AdapterResult> {
    return { ok: false, adapterId: this.id, operation: 'deploy', message: 'Deployment is intentionally external to Termux.' };
  }
}
