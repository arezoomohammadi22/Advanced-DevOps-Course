# Pulumi State and PostgreSQL Backend on Kubernetes

This project explains how Pulumi state works, where state can be stored, and how to migrate an existing Pulumi stack from a local backend to a PostgreSQL backend running inside Kubernetes.

The practical scenario uses:

- Ubuntu 24.04 as the Pulumi CLI host
- an existing Pulumi YAML project that manages Docker resources
- a Kubernetes cluster with dynamic storage provisioning
- PostgreSQL running as a Kubernetes `StatefulSet`
- a `PersistentVolumeClaim` for durable backend data
- `kubectl port-forward` for lab connectivity
- `pulumi stack export` and `pulumi stack import` for backend migration

> **Important:** Kubernetes itself is not a native Pulumi state backend. A Kubernetes `Secret` is not a Pulumi backend. In this architecture, Kubernetes only hosts PostgreSQL; PostgreSQL is the actual Pulumi backend.

---

## Table of Contents

- [1. Learning Objectives](#1-learning-objectives)
- [2. Core State Model](#2-core-state-model)
- [3. State, Program, Configuration, and Actual Infrastructure](#3-state-program-configuration-and-actual-infrastructure)
- [4. What Pulumi State Contains](#4-what-pulumi-state-contains)
- [5. Why State Is Critical](#5-why-state-is-critical)
- [6. Pulumi Backend Options](#6-pulumi-backend-options)
- [7. Backend Selection Guidance](#7-backend-selection-guidance)
- [8. Lab Architecture](#8-lab-architecture)
- [9. Prerequisites](#9-prerequisites)
- [10. Project Files](#10-project-files)
- [11. Verify the Existing Local Stack](#11-verify-the-existing-local-stack)
- [12. Export the Existing Local State](#12-export-the-existing-local-state)
- [13. Create the Kubernetes Namespace](#13-create-the-kubernetes-namespace)
- [14. Generate PostgreSQL Credentials](#14-generate-postgresql-credentials)
- [15. Create the PostgreSQL Services](#15-create-the-postgresql-services)
- [16. Create the PostgreSQL StatefulSet](#16-create-the-postgresql-statefulset)
- [17. Validate and Apply the Manifests](#17-validate-and-apply-the-manifests)
- [18. Verify PostgreSQL Inside Kubernetes](#18-verify-postgresql-inside-kubernetes)
- [19. Forward PostgreSQL to Ubuntu](#19-forward-postgresql-to-ubuntu)
- [20. Test PostgreSQL from Ubuntu](#20-test-postgresql-from-ubuntu)
- [21. Log In to the PostgreSQL Backend](#21-log-in-to-the-postgresql-backend)
- [22. Create the Destination Stack](#22-create-the-destination-stack)
- [23. Import the Existing Stack State](#23-import-the-existing-stack-state)
- [24. Validate the Migration](#24-validate-the-migration)
- [25. Apply a Controlled Update](#25-apply-a-controlled-update)
- [26. Confirm Shared Backend Access](#26-confirm-shared-backend-access)
- [27. Concurrency and Locking](#27-concurrency-and-locking)
- [28. Backup Strategy](#28-backup-strategy)
- [29. Restore Test](#29-restore-test)
- [30. Test Pod and Volume Persistence](#30-test-pod-and-volume-persistence)
- [31. Safe Cleanup](#31-safe-cleanup)
- [32. Production Requirements](#32-production-requirements)
- [33. Circular Dependency Warning](#33-circular-dependency-warning)
- [34. Pulumi Kubernetes Operator](#34-pulumi-kubernetes-operator)
- [35. Troubleshooting](#35-troubleshooting)
- [36. Final Mental Model](#36-final-mental-model)
- [37. Validation Checklist](#37-validation-checklist)

---

## 1. Learning Objectives

After completing this guide, you should be able to:

- explain why Pulumi requires state to manage resource lifecycles safely
- distinguish a Pulumi program from stack configuration, stack state, and actual infrastructure
- identify supported Pulumi backend categories
- explain why a Kubernetes `Secret` is not a native Pulumi backend
- run PostgreSQL inside Kubernetes with persistent storage
- connect an external Pulumi CLI to PostgreSQL through `kubectl port-forward`
- migrate a Pulumi stack from a local backend to PostgreSQL
- validate that imported state maps to existing resources
- perform stack-level and database-level backups
- run a restore test instead of assuming a backup is valid
- identify the limitations of this single-replica lab architecture

---

## 2. Core State Model

Pulumi state is the operational memory of a stack.

It records the relationship between:

- logical resources declared in the Pulumi program
- physical resources created by a provider
- resource inputs and outputs
- dependency relationships
- provider references
- the last successfully recorded deployment snapshot

For example, the Pulumi program may define a logical resource named `webContainer`, while Docker assigns a physical container ID such as:

```text
8ab3f3d8c5...
```

Pulumi state stores the relationship between the logical name and the physical provider ID. Without this relationship, Pulumi cannot safely know whether it should update an existing container, import it, create a duplicate, or fail because the resource already exists.

### State belongs to a stack

State is not one global file for the whole project. Each stack has its own independent state.

```text
One Pulumi project
├── dev     → dev state     → dev resources
├── staging → staging state → staging resources
└── prod    → prod state    → prod resources
```

The same `Pulumi.yaml` can be used by multiple stacks, while each stack has different resource IDs, configuration values, provider settings, endpoints, ports, outputs, and deployment history.

---

## 3. State, Program, Configuration, and Actual Infrastructure

These four concepts are different:

| Component | Purpose |
|---|---|
| `Pulumi.yaml` | Defines the desired resources and their relationships |
| `Pulumi.dev.yaml` | Stores stack-specific configuration values |
| Pulumi state | Stores the last recorded resource snapshot |
| Actual infrastructure | Represents what currently exists in Docker, Kubernetes, AWS, or another provider |

A drift scenario may look like this:

```text
Pulumi.yaml        → container should exist
Pulumi state       → container was recorded as existing
Actual Docker      → container was manually deleted
pulumi refresh     → records that the container is missing
pulumi up          → recreates the desired container
```

`pulumi refresh` updates the recorded state from the provider. It does not modify the Pulumi program and does not change the desired configuration.

---

## 4. What Pulumi State Contains

A stack snapshot can include:

1. **URN** — a stable logical identifier containing information such as the stack, project, resource type, and logical name.
2. **Physical provider ID** — for example, a Docker container ID, AWS ARN, or Kubernetes object identity.
3. **Resource type** — for example, `docker:Container` or `kubernetes:apps/v1:Deployment`.
4. **Inputs** — desired values sent to the provider, such as image name, labels, ports, or replica count.
5. **Outputs** — values returned by the provider, such as IDs, IP addresses, endpoints, or generated names.
6. **Dependencies** — relationships used to calculate create, update, replacement, and deletion order.
7. **Provider references** — the provider instance and configuration used for the resource.
8. **Parent-child relationships** — used by components and hierarchical resources.
9. **Lifecycle metadata** — examples include `protect`, `retainOnDelete`, aliases, and related options.
10. **Pending operations** — information that may help recovery after an interrupted update.

---

## 5. Why State Is Critical

### State drives preview and update planning

During `pulumi preview`:

```text
Pulumi program
    ↓
Desired resource graph
    ↓
Pulumi engine reads stack state
    ↓
Provider calculates differences
    ↓
Create / Update / Replace / Delete plan
```

During `pulumi up`, Pulumi executes the plan based on the dependency graph and writes updated checkpoints to the backend.

### Losing state does not automatically delete infrastructure

If state is lost:

- existing Docker, Kubernetes, or cloud resources may remain running
- Pulumi loses the logical-to-physical resource mapping
- preview may show existing resources as new
- duplicate resources may be created
- provider conflicts may occur
- manual imports or state recovery may be required

### Old state is also dangerous

Restoring an old snapshot can make Pulumi unaware of resources created after that snapshot. Backups must therefore include the stack identity, source backend, backup timestamp, secrets-provider requirements, recovery procedure, and restore validation.

### State can contain sensitive information

Inputs and outputs can contain passwords, tokens, connection strings, endpoints, infrastructure names, network information, and secret metadata.

Pulumi encrypts values explicitly marked as secrets, but secret encryption does not replace backend access control, encryption at rest, TLS, credential rotation, audit logging, or secure backup handling.

Never commit stack exports or backend database dumps to a public Git repository.

---

## 6. Pulumi Backend Options

A backend stores state for one or more projects and stacks.

### Pulumi Cloud

```bash
pulumi login
```

### Local filesystem

```bash
pulumi login --local
```

Typical use cases are training, local labs, isolated testing, and single-user development.

### AWS S3

```bash
pulumi login s3://my-pulumi-state-bucket
```

### S3-compatible storage

Examples include MinIO and Ceph Object Gateway. An endpoint and additional backend parameters may be required.

### Azure Blob Storage

```bash
pulumi login azblob://my-container
```

### Google Cloud Storage

```bash
pulumi login gs://my-pulumi-state-bucket
```

### PostgreSQL

```text
postgres://username:password@hostname:5432/database
```

> A Kubernetes `Secret` is not a supported backend URL or native state backend. The Pulumi Kubernetes Operator is also not a backend; it runs and reconciles Pulumi programs.

---

## 7. Backend Selection Guidance

Use a local backend for short-lived, single-user labs. Use Pulumi Cloud when managed collaboration and centralized controls are required. Use object storage when the organization already operates S3, Azure Blob, GCS, MinIO, or Ceph. Use PostgreSQL when the organization already has a reliable database platform with backup, monitoring, replication, TLS, and access controls.

Avoid storing cluster-management state inside the same cluster:

```text
Pulumi needs state
    ↓
State is inside the cluster
    ↓
Cluster is unavailable
    ↓
Pulumi cannot read the state required to recover the cluster
```

Use an external backend or a separate management cluster instead.

---

## 8. Lab Architecture

The existing project is assumed to be:

```text
~/pulumi-docker-yaml-lab/
├── Pulumi.yaml
├── Pulumi.dev.yaml
└── html/
    └── index.html
```

Migration flow:

```text
Existing Docker project
    ↓
Local backend in ~/.pulumi
    ↓ pulumi stack export
Checkpoint JSON backup
    ↓
Kubernetes cluster
├── Namespace
├── Kubernetes Secret
├── Headless Service
├── ClusterIP Service
├── PostgreSQL StatefulSet
└── PersistentVolumeClaim
    ↓ kubectl port-forward
Pulumi CLI on Ubuntu
    ↓ pulumi login postgres://...
PostgreSQL backend
    ↓ stack init + stack import
Same Docker resources, new state backend
```

Two independent paths exist:

```text
State path:
Pulumi CLI / Engine → PostgreSQL backend

Infrastructure path:
Pulumi Engine → Docker provider → Docker API / socket
```

PostgreSQL stores Pulumi state. The Docker provider continues to manage Docker.

---

## 9. Prerequisites

The Ubuntu host should have Ubuntu 24.04, Pulumi CLI, Docker Engine, `kubectl`, Kubernetes access, a dynamic storage provisioner, `openssl`, and access to the existing Pulumi Docker project.

Verify the environment:

```bash
pulumi version
docker version
kubectl version --client
kubectl cluster-info
kubectl get nodes
kubectl get storageclass
openssl version
```

Check the active cluster context:

```bash
kubectl config current-context
kubectl auth can-i create namespaces
```

---

## 10. Project Files

Create a working directory for the backend manifests:

```bash
mkdir -p ~/pulumi-postgres-backend
cd ~/pulumi-postgres-backend
```

Final layout:

```text
~/pulumi-postgres-backend/
├── pulumi-postgres-services.yaml
└── pulumi-postgres-statefulset.yaml
```

The Pulumi project remains in `~/pulumi-docker-yaml-lab/`.

---

## 11. Verify the Existing Local Stack

```bash
cd ~/pulumi-docker-yaml-lab
pulumi login --local
pulumi whoami -v
pulumi stack ls
pulumi stack select dev
pulumi stack
```

Confirm the existing resources:

```bash
docker ps --filter name=pulumi-nginx
docker network ls
pulumi preview
```

Do not continue if the existing stack is already in an unexpected state.

---

## 12. Export the Existing Local State

```bash
cd ~/pulumi-docker-yaml-lab
pulumi login --local
pulumi stack select dev
pulumi stack

pulumi stack export \
  --file ../pulumi-docker-dev-local.checkpoint.json
```

Create a checksum and inspect the file:

```bash
sha256sum ../pulumi-docker-dev-local.checkpoint.json
ls -lh ../pulumi-docker-dev-local.checkpoint.json
```

Restrict permissions:

```bash
chmod 600 ../pulumi-docker-dev-local.checkpoint.json
stat -c "%A %U:%G %n" \
  ../pulumi-docker-dev-local.checkpoint.json
```

`pulumi stack export` writes the current stack snapshot to JSON. It does not change Docker resources. Treat the export as sensitive and retain the original secrets-provider credentials or passphrase.

---

## 13. Create the Kubernetes Namespace

```bash
kubectl create namespace pulumi-backend

kubectl label namespace pulumi-backend \
  app.kubernetes.io/part-of=pulumi-state

kubectl get namespace pulumi-backend --show-labels
```

The namespace provides organization, not a complete security boundary. Production environments also require RBAC and network controls.

---

## 14. Generate PostgreSQL Credentials

Generate a random hexadecimal password:

```bash
export PULUMI_PG_USER='pulumi'
export PULUMI_PG_DB='pulumi_state'
export PULUMI_PG_PASSWORD="$(openssl rand -hex 24)"

test -n "$PULUMI_PG_PASSWORD" && \
  echo 'Password generated'
```

Create the Kubernetes secret:

```bash
kubectl -n pulumi-backend create secret generic \
  pulumi-postgres-auth \
  --from-literal=POSTGRES_USER="$PULUMI_PG_USER" \
  --from-literal=POSTGRES_PASSWORD="$PULUMI_PG_PASSWORD" \
  --from-literal=POSTGRES_DB="$PULUMI_PG_DB"
```

Verify metadata and key names without printing values:

```bash
kubectl -n pulumi-backend get secret \
  pulumi-postgres-auth

kubectl -n pulumi-backend describe secret \
  pulumi-postgres-auth
```

Kubernetes Secrets are base64-encoded by default. Base64 is not encryption. Use etcd encryption at rest, restricted RBAC, rotation, and an approved secret manager in production.

---

## 15. Create the PostgreSQL Services

Create `pulumi-postgres-services.yaml`:

```bash
cd ~/pulumi-postgres-backend

cat > pulumi-postgres-services.yaml <<'EOF'
apiVersion: v1
kind: Service
metadata:
  name: pulumi-postgres-headless
  namespace: pulumi-backend
  labels:
    app.kubernetes.io/name: pulumi-postgres
spec:
  clusterIP: None
  selector:
    app.kubernetes.io/name: pulumi-postgres
  ports:
    - name: postgres
      port: 5432
      targetPort: postgres
---
apiVersion: v1
kind: Service
metadata:
  name: pulumi-postgres
  namespace: pulumi-backend
  labels:
    app.kubernetes.io/name: pulumi-postgres
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: pulumi-postgres
  ports:
    - name: postgres
      protocol: TCP
      port: 5432
      targetPort: postgres
EOF
```

The headless service is the governing service for the `StatefulSet`. The `ClusterIP` service provides a stable client endpoint and is used by `kubectl port-forward`. No public `NodePort` or `LoadBalancer` is created.

---

## 16. Create the PostgreSQL StatefulSet

Create `pulumi-postgres-statefulset.yaml`:

```bash
cat > pulumi-postgres-statefulset.yaml <<'EOF'
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: pulumi-postgres
  namespace: pulumi-backend
  labels:
    app.kubernetes.io/name: pulumi-postgres
spec:
  serviceName: pulumi-postgres-headless
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: pulumi-postgres
  template:
    metadata:
      labels:
        app.kubernetes.io/name: pulumi-postgres
    spec:
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 30
      containers:
        - name: postgres
          image: postgres:16-alpine
          imagePullPolicy: IfNotPresent
          ports:
            - name: postgres
              containerPort: 5432
              protocol: TCP
          envFrom:
            - secretRef:
                name: pulumi-postgres-auth
          env:
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
          readinessProbe:
            exec:
              command:
                - sh
                - -c
                - pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 6
          livenessProbe:
            exec:
              command:
                - sh
                - -c
                - pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
            initialDelaySeconds: 25
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 6
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
  volumeClaimTemplates:
    - metadata:
        name: postgres-data
      spec:
        accessModes:
          - ReadWriteOnce
        resources:
          requests:
            storage: 5Gi
EOF
```

Notes:

- `StatefulSet` provides stable identity and storage behavior.
- `volumeClaimTemplates` creates a PVC such as `postgres-data-pulumi-postgres-0`.
- `PGDATA` uses a subdirectory inside the mounted volume.
- readiness controls service eligibility.
- liveness detects a long-running failed process.
- resource values are for the lab only.
- production should pin and test an exact image version or digest.

---

## 17. Validate and Apply the Manifests

Run server-side dry runs:

```bash
cd ~/pulumi-postgres-backend

kubectl apply --dry-run=server \
  -f pulumi-postgres-services.yaml

kubectl apply --dry-run=server \
  -f pulumi-postgres-statefulset.yaml
```

Apply the resources:

```bash
kubectl apply -f pulumi-postgres-services.yaml
kubectl apply -f pulumi-postgres-statefulset.yaml
```

Kubernetes flow:

```text
kubectl apply
    ↓
Kubernetes API Server
    ↓
StatefulSet controller creates pulumi-postgres-0
    ↓
Scheduler selects a node
    ↓
PVC controller and CSI provisioner create storage
    ↓
Kubelet pulls postgres:16-alpine
    ↓
Secret values initialize PostgreSQL
    ↓
Readiness probe succeeds
```

Wait for rollout:

```bash
kubectl -n pulumi-backend rollout status \
  statefulset/pulumi-postgres \
  --timeout=180s
```

Inspect resources:

```bash
kubectl -n pulumi-backend get pods -o wide
kubectl -n pulumi-backend get services
kubectl -n pulumi-backend get pvc
kubectl -n pulumi-backend get endpoints pulumi-postgres
```

Expected conditions:

- pod is `Running`
- readiness is `1/1`
- PVC is `Bound`
- the service has an endpoint on port `5432`

Initial troubleshooting:

```bash
kubectl -n pulumi-backend describe pvc \
  postgres-data-pulumi-postgres-0

kubectl -n pulumi-backend describe pod \
  pulumi-postgres-0

kubectl -n pulumi-backend logs \
  statefulset/pulumi-postgres \
  --tail=100
```

---

## 18. Verify PostgreSQL Inside Kubernetes

```bash
kubectl -n pulumi-backend exec \
  statefulset/pulumi-postgres -- \
  sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Run a real query:

```bash
kubectl -n pulumi-backend exec \
  statefulset/pulumi-postgres -- \
  sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT current_database(), current_user, version();"'
```

The first command checks availability. The second proves that authenticated SQL queries work.

---

## 19. Forward PostgreSQL to Ubuntu

Run this in a dedicated terminal and keep it open:

```bash
kubectl -n pulumi-backend port-forward \
  service/pulumi-postgres \
  15432:5432
```

Connection path:

```text
Pulumi CLI on Ubuntu
    ↓ 127.0.0.1:15432
kubectl port-forward
    ↓
pulumi-postgres service
    ↓
PostgreSQL pod:5432
```

In a second terminal:

```bash
ss -lnt | grep 15432
nc -zv 127.0.0.1 15432
```

The tunnel stops if the terminal closes, the pod restarts, or the API connection is interrupted.

---

## 20. Test PostgreSQL from Ubuntu

Reload credentials if necessary:

```bash
export PULUMI_PG_USER="$(
  kubectl -n pulumi-backend get secret \
    pulumi-postgres-auth \
    -o jsonpath='{.data.POSTGRES_USER}' | \
  base64 --decode
)"

export PULUMI_PG_DB="$(
  kubectl -n pulumi-backend get secret \
    pulumi-postgres-auth \
    -o jsonpath='{.data.POSTGRES_DB}' | \
  base64 --decode
)"

export PULUMI_PG_PASSWORD="$(
  kubectl -n pulumi-backend get secret \
    pulumi-postgres-auth \
    -o jsonpath='{.data.POSTGRES_PASSWORD}' | \
  base64 --decode
)"

test -n "$PULUMI_PG_PASSWORD" && \
  echo 'Database credentials loaded'
```

Install the client:

```bash
sudo apt-get update
sudo apt-get install -y postgresql-client
```

Test the connection:

```bash
PGPASSWORD="$PULUMI_PG_PASSWORD" psql \
  --host=127.0.0.1 \
  --port=15432 \
  --username="$PULUMI_PG_USER" \
  --dbname="$PULUMI_PG_DB" \
  --command="SELECT current_database(), current_user;"
```

A successful query confirms PostgreSQL, the service endpoint, port forwarding, and the credentials.

If a custom password includes URL-reserved characters, URL-encode it:

```bash
export PULUMI_PG_PASSWORD_ENCODED="$(
  python3 -c 'import os, urllib.parse; print(urllib.parse.quote(os.environ["PULUMI_PG_PASSWORD"], safe=""))'
)"
```

---

## 21. Log In to the PostgreSQL Backend

The lab password is hexadecimal, so it can be used directly:

```bash
export PULUMI_BACKEND_URL="postgres://${PULUMI_PG_USER}:${PULUMI_PG_PASSWORD}@127.0.0.1:15432/${PULUMI_PG_DB}?sslmode=disable"
```

Switch backend context:

```bash
pulumi logout
pulumi login "$PULUMI_BACKEND_URL"
pulumi whoami -v
```

- `pulumi logout` closes the current backend session but does not delete old state.
- `pulumi login` changes the active backend.
- `pulumi whoami -v` displays backend information.

These commands do not create Docker or Kubernetes resources.

`sslmode=disable` is only for this loopback lab. Production connections require TLS and certificate validation. Do not publish output that exposes the backend URL.

---

## 22. Create the Destination Stack

```bash
cd ~/pulumi-docker-yaml-lab
pulumi stack ls
pulumi stack init dev
pulumi stack ls
```

A `dev` stack on the local backend and a `dev` stack on PostgreSQL are different objects because their backend contexts are different.

`Pulumi.dev.yaml` may already contain stack configuration, but the destination backend state is empty until import.

If `dev` already exists on PostgreSQL, do not delete it immediately. Select and export it first to determine whether the backend was already used.

---

## 23. Import the Existing Stack State

```bash
pulumi stack select dev

pulumi stack import \
  --file ../pulumi-docker-dev-local.checkpoint.json

pulumi stack

pulumi stack export \
  --file ../pulumi-docker-dev-postgres.checkpoint.json
```

Import writes the existing deployment snapshot to PostgreSQL. It does not recreate Docker resources.

Source and destination exports may differ in metadata or serialization. Validate the resource inventory, URNs, physical IDs, outputs, and preview instead of comparing only hashes.

If encrypted configuration or outputs exist, retain the original passphrase or secrets-provider access. Backend migration and secrets-provider migration are separate concerns.

---

## 24. Validate the Migration

```bash
pulumi preview
pulumi stack --show-urns
pulumi stack output
```

Expected result is `No changes` or only known, expected differences.

If every resource appears as new, do not approve `pulumi up`. Check the active backend, selected stack, project name, logical resource names, checkpoint path, URNs, provider configuration, and Docker connectivity.

Correct mapping requires:

```text
Program resource URN
    ↕
Imported state URN
    ↕
Existing Docker physical resource ID
```

---

## 25. Apply a Controlled Update

Change the host port:

```bash
pulumi config set hostPort 8081
pulumi preview
pulumi up
```

A Docker port mapping change may replace the container. Inspect preview before approval.

Validate the update:

```bash
curl -i http://127.0.0.1:8081
docker ps --filter name=pulumi-nginx
pulumi stack output applicationUrl
pulumi stack history
```

This proves that Pulumi can read migrated state, run provider operations, write a new checkpoint, and store update history.

---

## 26. Confirm Shared Backend Access

On another authorized machine, connect to the same cluster and backend:

```bash
kubectl -n pulumi-backend port-forward \
  service/pulumi-postgres \
  15432:5432
```

In another terminal:

```bash
export PULUMI_BACKEND_URL='postgres://pulumi:<secret>@127.0.0.1:15432/pulumi_state?sslmode=disable'

pulumi login "$PULUMI_BACKEND_URL"
cd pulumi-docker-yaml-lab
pulumi stack ls
pulumi stack select dev
pulumi preview
```

Seeing `dev` proves that state is shared through PostgreSQL rather than tied to the first machine.

Shared state does not automatically provide provider connectivity. The second machine must also reach the Docker daemon or other provider target.

---

## 27. Concurrency and Locking

Do not remove an update lock while another user or pipeline is active.

For a genuinely stale operation:

```bash
pulumi cancel
pulumi preview
```

`pulumi cancel` does not roll back provider-side actions. Inspect actual resources and consider `pulumi refresh` before another update.

---

## 28. Backup Strategy

Use both stack-level and database-level backups.

Create a protected directory:

```bash
mkdir -p ~/pulumi-backups
chmod 700 ~/pulumi-backups
```

Stack backup:

```bash
pulumi stack export \
  --file ~/pulumi-backups/dev-$(date +%F-%H%M).checkpoint.json

chmod 600 ~/pulumi-backups/*.checkpoint.json
ls -lh ~/pulumi-backups
```

Database backup:

```bash
kubectl -n pulumi-backend exec \
  statefulset/pulumi-postgres -- \
  pg_dump -U pulumi -d pulumi_state -Fc \
  > ~/pulumi-backups/pulumi-state-$(date +%F-%H%M).dump

chmod 600 ~/pulumi-backups/*.dump

pg_restore --list \
  ~/pulumi-backups/pulumi-state-*.dump | \
  head
```

Copy backups outside the Kubernetes failure domain and apply retention, encryption, access controls, integrity checks, and restore testing.

---

## 29. Restore Test

Create a temporary database:

```bash
kubectl -n pulumi-backend exec \
  statefulset/pulumi-postgres -- \
  sh -lc 'createdb -U "$POSTGRES_USER" pulumi_state_restore_test'
```

Restore the dump:

```bash
cat ~/pulumi-backups/pulumi-state-*.dump | \
  kubectl -n pulumi-backend exec -i \
    statefulset/pulumi-postgres -- \
  pg_restore \
    -U pulumi \
    -d pulumi_state_restore_test
```

Inspect restored tables:

```bash
kubectl -n pulumi-backend exec \
  statefulset/pulumi-postgres -- \
  psql \
    -U pulumi \
    -d pulumi_state_restore_test \
    -c '\dt'
```

Delete the test database:

```bash
kubectl -n pulumi-backend exec \
  statefulset/pulumi-postgres -- \
  dropdb -U pulumi pulumi_state_restore_test
```

Production recovery requires documented RPO, RTO, point-in-time recovery, validation, rollback, isolation, and change approval. Never restore over the active backend without a tested plan.

---

## 30. Test Pod and Volume Persistence

Delete the PostgreSQL pod:

```bash
kubectl -n pulumi-backend delete pod \
  pulumi-postgres-0

kubectl -n pulumi-backend get pods -w
```

The `StatefulSet` creates a replacement and reattaches the PVC.

After readiness:

1. restart `kubectl port-forward`
2. reconnect to the backend if necessary
3. run:

```bash
pulumi stack ls
```

If state is still available, persistent storage worked. This does not prove high availability because the single-replica backend was unavailable during restart.

Deleting a pod normally preserves the PVC. Deleting the PVC or namespace can remove or orphan the volume depending on reclaim policy.

Never delete the backend namespace before protecting or migrating the state.

---

## 31. Safe Cleanup

### Keep the backend

Stop port forwarding and clear variables:

```bash
unset PULUMI_BACKEND_URL
unset PULUMI_PG_USER
unset PULUMI_PG_DB
unset PULUMI_PG_PASSWORD
unset PULUMI_PG_PASSWORD_ENCODED
```

### Remove the complete lab

Safe order:

1. export final state
2. destroy managed resources while the backend is available
3. remove the stack record
4. log out
5. delete backend resources
6. clear credentials

Destroy Pulumi-managed Docker resources:

```bash
cd ~/pulumi-docker-yaml-lab
pulumi stack select dev

pulumi stack export \
  --file ~/pulumi-backups/dev-final.checkpoint.json

pulumi destroy
pulumi stack rm dev
pulumi logout
```

Remove Kubernetes backend resources:

```bash
cd ~/pulumi-postgres-backend

kubectl delete -f pulumi-postgres-statefulset.yaml
kubectl delete -f pulumi-postgres-services.yaml
kubectl -n pulumi-backend delete secret \
  pulumi-postgres-auth
kubectl delete namespace pulumi-backend
```

Clear variables:

```bash
unset PULUMI_BACKEND_URL
unset PULUMI_PG_USER
unset PULUMI_PG_DB
unset PULUMI_PG_PASSWORD
unset PULUMI_PG_PASSWORD_ENCODED
```

`pulumi destroy` deletes managed infrastructure. `pulumi stack rm` removes the stack record from the active backend. Avoid `pulumi stack rm --force` because it can orphan real resources.

---

## 32. Production Requirements

This lab is not production-ready because it uses one PostgreSQL replica, temporary port forwarding, no database TLS, basic secret handling, and no external HA design.

Production should include:

- PostgreSQL HA and tested failover
- scheduled backups and off-cluster copies
- retention and periodic restore tests
- TLS with certificate validation
- credential rotation and a secret manager
- restricted RBAC and etcd encryption at rest
- Kubernetes `NetworkPolicy`
- database connection restrictions
- monitoring for database, disk, replication, and backup failures
- `PodDisruptionBudget` and anti-affinity
- capacity planning
- tested storage class and reclaim policy
- snapshots and disaster recovery in another cluster or region
- runbooks for backend outage, stale locks, and partial updates

---

## 33. Circular Dependency Warning

Do not use this PostgreSQL instance as the backend for a stack that creates or destroys the same Kubernetes cluster hosting PostgreSQL.

```text
Unsafe:
Pulumi needs state → state is inside target cluster → cluster fails → recovery state is unavailable

Safer:
Cluster-management stack → external backend or management cluster
Application stacks → approved external/shared backend
```

---

## 34. Pulumi Kubernetes Operator

The Pulumi Kubernetes Operator can run Pulumi programs inside workspace pods. In that case the backend can use the internal service DNS:

```text
postgres://pulumi:<secret>@pulumi-postgres.pulumi-backend.svc.cluster.local:5432/pulumi_state?sslmode=require
```

The operator runs the program; PostgreSQL remains the backend. Removing the operator should not remove state. The operator is not installed by this guide.

---

## 35. Troubleshooting

### PVC remains `Pending`

```bash
kubectl get storageclass

kubectl -n pulumi-backend describe pvc \
  postgres-data-pulumi-postgres-0

kubectl get events \
  -n pulumi-backend \
  --sort-by=.lastTimestamp | \
  tail -30
```

### Pod is in `CrashLoopBackOff`

```bash
kubectl -n pulumi-backend logs \
  pulumi-postgres-0 \
  --previous

kubectl -n pulumi-backend describe pod \
  pulumi-postgres-0
```

Common causes include volume permissions, missing secret keys, incompatible existing data, insufficient resources, and image pull failures.

### Port forward exists but connection is refused

```bash
kubectl -n pulumi-backend get endpoints \
  pulumi-postgres

kubectl -n pulumi-backend get pod \
  pulumi-postgres-0

ss -lnt | grep 15432
```

Restart port forwarding if the pod restarted.

### `pulumi login` authentication failure

Test the same credentials with `psql`. If `psql` fails, solve database, secret, forwarding, or URL issues before troubleshooting Pulumi.

### Preview proposes creating every resource after import

Do not run `pulumi up`.

```bash
pulumi whoami -v
pulumi stack ls
pulumi stack --show-urns
pulumi preview
```

Check backend, stack, project name, logical names, URNs, checkpoint path, provider configuration, and Docker connectivity.

### Backend unavailable while Docker resources still run

Recover PostgreSQL and the network path first. If recovery is impossible, restore a database dump or import a protected checkpoint into a new backend, then run and inspect `pulumi preview` before applying changes.

### Stale update lock

After verifying no process or pipeline is active:

```bash
pulumi cancel
pulumi preview
```

Inspect actual resources and consider `pulumi refresh` because cancellation does not undo provider operations.

---

## 36. Final Mental Model

```text
Pulumi program
    = desired infrastructure definition

Provider
    = communication with Docker, Kubernetes, AWS, or another API

State
    = recorded identities, inputs, outputs, dependencies, and checkpoints

Backend
    = storage and coordination layer for stack state

Actual infrastructure
    = resources that exist right now
```

For this project:

```text
Kubernetes hosts PostgreSQL
PostgreSQL stores Pulumi state
Pulumi CLI reads and writes state through PostgreSQL
Docker provider continues to manage Docker resources
```

The backend path and provider path are separate.

---

## 37. Validation Checklist

- [ ] I can explain why state is required for safe updates and deletion.
- [ ] I can distinguish program, stack config, state, backend, and actual infrastructure.
- [ ] I understand that a Kubernetes `Secret` is not a native Pulumi backend.
- [ ] I exported and protected the source checkpoint before migration.
- [ ] PostgreSQL is ready and its PVC is bound.
- [ ] The service has a valid endpoint.
- [ ] PostgreSQL works inside Kubernetes and from Ubuntu.
- [ ] Pulumi is logged in to PostgreSQL.
- [ ] The old checkpoint was imported.
- [ ] Preview shows no unexpected recreation.
- [ ] A controlled update was written to PostgreSQL.
- [ ] A stack backup and database dump were created.
- [ ] The database dump passed a restore test.
- [ ] I understand the risk of deleting the backend before destroying managed resources.
- [ ] I understand the HA, TLS, RBAC, monitoring, backup, and recovery requirements for production.

---

## References

- Pulumi documentation: State and Backends
- Pulumi documentation: Using a DIY Backend
- Pulumi CLI: `pulumi login`
- Pulumi CLI: `pulumi stack export`
- Pulumi CLI: `pulumi stack import`
- Pulumi documentation: Secrets Handling
- Pulumi Kubernetes Operator documentation
- Kubernetes documentation: StatefulSets
- Kubernetes documentation: Persistent Volumes
- Kubernetes documentation: Secrets
- Kubernetes documentation: `kubectl port-forward`

Before using this design in production, verify current software versions, provider behavior, storage policies, security standards, and organizational recovery requirements.

