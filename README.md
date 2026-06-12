# Event Processor

Lightweight microservice demo for testing Kubernetes deployment patterns with ArgoCD + Kustomize.

## Architecture

```
┌──────────────┐       ┌───────┐       ┌───────────┐
│ ingestion-api│──────▶│ Redis │◀──────│ processor │
│  (Deployment)│ RPUSH │ (list)│ LPOP  │ (CronJob) │
└──────────────┘       └───┬───┘       └───────────┘
                           │
                      events:dlq
                   (malformed events)
```

- **ingestion-api** — HTTP service accepting `POST /events`, pushes to a Redis list. Runs as a `Deployment`. Health check at `/health` validates Redis connectivity — pod is pulled from the load balancer if Redis is unreachable.
- **processor** — Batch worker that drains the queue. Runs as a `CronJob` (every 5 min in dev, every 2 min in prod). Malformed events are moved to `events:dlq` rather than dropped. Exits with code `1` on Redis connection failure so Kubernetes `backoffLimit` retries apply.
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
  argocd/               # ArgoCD Application manifests (applied once to bootstrap)
    app-dev.yaml
    app-prod.yaml

.github/
  workflows/
    ci.yaml             # Builds images, pushes to DockerHub, updates overlay image tags
```

## CI / CD Flow

```
git push → GitHub Actions CI
              ├── builds services/ingestion-api → docker.io/chetback/ingestion-api:<sha>
              ├── builds services/processor     → docker.io/chetback/processor:<sha>
              └── runs kustomize edit set image → commits updated k8s/overlays/dev/

ArgoCD detects manifest change → syncs to cluster → rolls out new pods
```

Requires two secrets in the repository: `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`.

## ArgoCD Integration

App manifests live in `k8s/argocd/` and are applied once to bootstrap:

```bash
kubectl apply -f k8s/argocd/app-dev.yaml
```

ArgoCD watches `k8s/overlays/dev` (never `k8s/base/` directly). The `CreateNamespace=true` sync option means the `event-processor` namespace is created automatically on first sync.

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
# Port-forward the ingestion API
kubectl port-forward svc/ingestion-api -n event-processor 8080:80

# Send an event
curl -X POST http://localhost:8080/events \
  -H "Content-Type: application/json" \
  -d '{"type": "user.signup", "user_id": "abc123"}'

# Check queue depth
curl http://localhost:8080/queue/length

# Check health (Redis connectivity)
curl http://localhost:8080/health

# Manually trigger processor instead of waiting for cron
kubectl create job --from=cronjob/processor manual-run -n event-processor

# Watch processor logs
kubectl logs -n event-processor -l app=processor -f

# Inspect dead-letter queue
kubectl port-forward svc/redis -n event-processor 6379:6379
redis-cli lrange events:dlq 0 -1
```
