import { AdapterRegistry } from './AdapterRegistry';
import { CustomerViteAdapter } from './adapters/CustomerViteAdapter';
import { TermuxAdapter } from './adapters/TermuxAdapter';
import { VercelProductionAdapter } from './adapters/VercelProductionAdapter';

export function createDefaultAdapterRegistry(): AdapterRegistry {
  const registry = new AdapterRegistry();
  registry.register(new TermuxAdapter());
  registry.register(new VercelProductionAdapter());
  registry.register(new CustomerViteAdapter());
  return registry;
}

export * from './TargetAdapter';
export * from './AdapterRegistry';
export * from './adapters/CustomerViteAdapter';
export * from './adapters/TermuxAdapter';
export * from './adapters/VercelProductionAdapter';
