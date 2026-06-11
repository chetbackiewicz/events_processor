# Event Pipeline Demo

Lightweight microservice demo for testing Kubernetes deployment patterns with ArgoCD + Kustomize.

## Architecture

```
┌──────────────┐       ┌───────┐       ┌───────────┐
│ ingestion-api│──────▶│ Redis │◀──────│ processor │
│  (Deployment)│ RPUSH │ (list)│ LPOP  │ (CronJob) │
└──────────────┘       └───────┘       └───────────┘
```

- **ingestion-api** — HTTP service accepting POST `/events`, pushes to a Redis list. Runs as a `Deployment`.
- **processor** — Batch worker that drains the queue. Runs as a `CronJob` (every 5 min in dev, every 2 min in prod).
- **Redis** — Lightweight queue (Redis list) connecting the two services.

## Repository Layout

```
services/               # Application source code + Dockerfiles only
  ingestion-api/
  processor/

k8s/
  base/                 # Canonical manifests (Kustomize base)
    kustomization.yaml
    namespace.yaml
    redis/
    ingestion-api/
    processor/
  overlays/
    dev/                # Dev patches (low replicas, small resources)
    prod/               # Prod patches (higher replicas, bigger limits)
```

## ArgoCD Integration

Point ArgoCD at an overlay directory — **never at `k8s/base/` directly**:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: event-pipeline-dev
  namespace: argocd
spec:
  source:
    repoURL: https://github.com/chetbackiewicz/demo.git
    targetRevision: main
    path: k8s/overlays/dev
  destination:
    server: https://kubernetes.default.svc
    namespace: event-pipeline
  project: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## Local Development

```bash
# Build images
docker build -t ingestion-api:dev services/ingestion-api/
docker build -t processor:dev services/processor/

# Validate manifests
kubectl kustomize k8s/overlays/dev

# Apply locally (kind/minikube)
kubectl apply -k k8s/overlays/dev
```

## Testing the Pipeline

```bash
# Send an event
curl -X POST http://localhost:8080/events \
  -H "Content-Type: application/json" \
  -d '{"type": "user.signup", "user_id": "abc123"}'

# Check queue depth
curl http://localhost:8080/queue/length

# Manually trigger processor (instead of waiting for cron)
kubectl create job --from=cronjob/processor manual-run -n event-pipeline
```
