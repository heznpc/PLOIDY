# Deploying Ploidy 0.4.0

All checked-in deployment recipes use
`ghcr.io/heznpc/ploidy:0.4.0`. They run one replica because persistence
is a local SQLite file.

- [Fly.io](fly/README.md): HTTPS with controlled static bearer admission
- [Plain Kubernetes](kubernetes/ploidy.yaml): single-file baseline
- [Helm](helm/ploidy/): configurable chart with optional
  ServiceMonitor and NetworkPolicy

Every recipe enables bounded service defaults:

| Setting | Default |
|---|---:|
| `PLOIDY_MAX_CONTEXT_DOCS` | `10` |
| `PLOIDY_MAX_CONTEXT_TOKENS` | `20000` |
| `PLOIDY_RATE_CAPACITY` | `20` |
| `PLOIDY_RATE_PER_SEC` | `1` |
| `PLOIDY_RETENTION_DAYS` | `30` |

## Helm with static bearer authentication

Create the token secret outside Helm so it is not stored in shell
history as a chart value:

```bash
export PLOIDY_API_TOKEN=$(openssl rand -hex 32)
kubectl create secret generic ploidy-auth \
  --from-literal=PLOIDY_TOKENS="{\"$PLOIDY_API_TOKEN\":\"tenant-a\"}"

helm install ploidy deploy/helm/ploidy \
  --set existingSecret=ploidy-auth
```

The chart's default image tag and `appVersion` are both `0.4.0`.

## Helm OAuth interoperability test

OAuth mode in 0.4.0 auto-approves dynamically registered clients and has
no resource-owner login or consent. Run it only behind controlled ingress;
it is not sufficient public access control or directory-ready auth.

```bash
helm install ploidy deploy/helm/ploidy \
  --set-string env.PLOIDY_AUTH_MODE=oauth \
  --set-string env.PLOIDY_OAUTH_ISSUER=https://ploidy.example.com
```

The issuer must be the exact public HTTPS origin. Configure ingress and
TLS separately for your cluster.

Useful chart switches:

- `persistence.size`: PVC capacity
- `serviceMonitor.enabled`: Prometheus Operator integration
- `networkPolicy.enabled`: restrict ingress
- `existingSecret`: externally managed static/API/dashboard secrets
- `env.PLOIDY_*`: explicit service configuration

## Plain Kubernetes

The single-file manifest contains an example Secret. Replace its blank
credentials and choose `bearer`, `oauth`, or `both` before exposing the
Service through ingress:

```bash
kubectl apply -f deploy/kubernetes/ploidy.yaml
```

Blank bearer credentials mean unauthenticated local operation; they are
not a production configuration.

## Scaling and metrics

Do not increase replicas beyond one while using the SQLite PVC. Redis
can coordinate process locks, but it does not replace the state store.

`/metrics` is intentionally an infrastructure endpoint. Restrict it with
a NetworkPolicy, ingress rule, or private monitoring path.
