# Phase 31 External Runtime Boundary

Termux builds and validates the provider-neutral source. The following are intentionally **not** executed locally:

1. Docker daemon / Docker Compose service orchestration.
2. NVIDIA CUDA/vLLM inference runtime.
3. Managed cloud deployment and IAM mutations.
4. Production databases, Redis/streams, MQTT/EMQX brokers, and secret managers.
5. DNS/domain changes and Cloudflare production routing.

The repository may contain manifests/configuration for these systems, but execution belongs to CI or a Linux/cloud runtime with the required credentials and hardware.
