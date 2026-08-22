import type { AdapterContext, TargetAdapter } from './TargetAdapter';

export class AdapterRegistry {
  private readonly adapters = new Map<string, TargetAdapter>();

  register(adapter: TargetAdapter): void {
    if (this.adapters.has(adapter.id)) {
      throw new Error(`adapter_already_registered:${adapter.id}`);
    }
    this.adapters.set(adapter.id, adapter);
  }

  get(id: string): TargetAdapter | undefined {
    return this.adapters.get(id);
  }

  list(): TargetAdapter[] {
    return [...this.adapters.values()];
  }

  async select(operation: 'inspect' | 'plan' | 'build' | 'test' | 'deploy' | 'rollback', context: AdapterContext): Promise<TargetAdapter[]> {
    const candidates: TargetAdapter[] = [];
    for (const adapter of this.adapters.values()) {
      const capabilities = await adapter.capabilities(context);
      if (capabilities.some((capability) => capability.operation === operation && capability.supported)) {
        candidates.push(adapter);
      }
    }
    return candidates;
  }
}
