export interface RuntimeCapability {
  name: string;
  local: boolean;
  external: boolean;
  reason: string;
}

export const PHASE31_CAPABILITIES: RuntimeCapability[] = [
  { name: 'python_backend', local: true, external: false, reason: 'Termux supports Python execution.' },
  { name: 'node_frontend', local: true, external: false, reason: 'Node/npm can run the frontend toolchain on supported Termux builds.' },
  { name: 'git_source_sync', local: true, external: false, reason: 'Git operations are available in Termux.' },
  { name: 'docker_daemon', local: false, external: true, reason: 'Termux does not provide a native Docker daemon; use a remote Linux host or compatible daemon.' },
  { name: 'nvidia_vllm', local: false, external: true, reason: 'The current Android/Termux target is not treated as an NVIDIA GPU execution host.' },
  { name: 'cloud_deployment', local: false, external: true, reason: 'Deployment requires provider credentials and external infrastructure.' }
];
