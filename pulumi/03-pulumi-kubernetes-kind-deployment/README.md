# Deploying a Kubernetes Application with Pulumi and Kind

This guide uses Pulumi, TypeScript, Kubernetes, and Kind to build and manage a complete local application environment. It starts with cluster creation and kubeconfig validation, then defines an explicit Kubernetes provider, a stack-specific namespace, a ConfigMap, an Nginx Deployment, health probes, resource requests and limits, a ConfigMap-backed volume, and a NodePort Service. It continues through deployment validation, scaling, rolling updates, content changes, drift detection, state reconciliation, multiple stacks, troubleshooting, and complete cleanup.

The cluster is local so that the entire workflow can be practiced without a cloud account or managed-Kubernetes cost. The same Kubernetes resources can later be deployed to EKS, AKS, GKE, OpenShift, or another conformant cluster by changing the provider connection and environment-specific configuration.

---

## Learning Outcomes

After completing this guide, you should be able to:

- Explain the relationship between a Pulumi program, the Kubernetes provider, kubeconfig, a Kubernetes context, and the API server.
- Create a Kind cluster with fixed host-to-node port mappings.
- Verify cluster health before starting an IaC deployment.
- Create a TypeScript Pulumi project and install `@pulumi/kubernetes`.
- Configure Pulumi to use an explicit Kubernetes context instead of relying on whichever context happens to be current.
- Create a namespace for each stack.
- Use labels and selectors to connect Deployments, Pods, and Services.
- Store web content in a ConfigMap and mount it into a container.
- Configure Deployment replicas, rolling-update strategy, Pod templates, resources, readiness, liveness, and volumes.
- Expose the application through a NodePort Service in a local Kind environment.
- Validate the deployment with Pulumi outputs, `kubectl`, rollout status, logs, describe output, and `curl`.
- Scale the workload, change the image, and force a rollout when configuration-backed content changes.
- Introduce controlled drift with `kubectl`, refresh Pulumi state, and restore the desired state.
- Create independent `dev` and `staging` stacks in one cluster without namespace, NodePort, or host-port collisions.
- Explain the difference between Pulumi state and Kubernetes control-plane state.
- Troubleshoot context, cluster, NodePort, image-pull, readiness, rollout, and unexpected replacement failures.
- Destroy application stacks before deleting the underlying cluster.

---

## Architecture

The final request path for development is:

```text
Browser or curl
    |
    v
127.0.0.1:8080 on the host
    |
    v
Kind container port 30080
    |
    v
Kubernetes NodePort Service
    |
    v
Service selector
    |
    v
Ready Nginx Pods on container port 80
```

Staging uses a separate path:

```text
127.0.0.1:8081
    -> Kind node port 30081
    -> staging NodePort Service
    -> staging Pods
```

The Pulumi resource graph contains:

1. An explicit Kubernetes provider
2. A namespace whose name includes the active stack
3. A ConfigMap in that namespace
4. A Deployment that references the namespace and ConfigMap
5. A Service that selects the Deployment's Pods
6. Stack outputs for resource names, desired replicas, and the local URL

Pulumi manages the lifecycle of these Kubernetes objects. Kubernetes controllers manage the continuous runtime reconciliation inside the cluster. Both systems maintain state, but they have different responsibilities.

---

## Prerequisites

Install:

- Docker Engine or Docker Desktop
- Kind
- `kubectl`
- Pulumi CLI
- Node.js LTS
- npm
- Git, recommended
- A code editor, recommended

Verify all tools:

```bash
docker version
kind version
kubectl version --client
pulumi version
node --version
npm --version
```

Verify Docker independently:

```bash
docker info
docker ps
```

Kind runs Kubernetes nodes as Docker containers. If Docker is not healthy, the cluster cannot be created and the Pulumi Kubernetes provider will have no API server to target.

---

## Create the Working Directories

```bash
mkdir pulumi-k8s-lab
cd pulumi-k8s-lab
mkdir cluster
mkdir infra
```

The directory layout separates cluster bootstrap from application infrastructure:

```text
pulumi-k8s-lab/
├── cluster/
│   └── kind-config.yaml
└── infra/
    ├── Pulumi.yaml
    ├── Pulumi.dev.yaml
    ├── index.ts
    ├── package.json
    ├── package-lock.json
    ├── tsconfig.json
    └── node_modules/
```

In a larger repository, cluster provisioning and in-cluster workloads may be separate projects or repositories with separate ownership and deployment pipelines. They are kept close here to make the complete flow visible.

---

## Create the Kind Cluster Configuration

Create `cluster/kind-config.yaml`:

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: pulumi-lab
nodes:
  - role: control-plane
    extraPortMappings:
      - containerPort: 30080
        hostPort: 8080
        listenAddress: "127.0.0.1"
        protocol: TCP
      - containerPort: 30081
        hostPort: 8081
        listenAddress: "127.0.0.1"
        protocol: TCP
```

### Why port mapping is required

A Kind node is itself a Docker container. A Kubernetes NodePort opens a port on the node, but the node is not the host operating system. `extraPortMappings` forwards host traffic into the node container.

The numbers must align:

- Development Service `nodePort`: `30080`
- Kind `containerPort`: `30080`
- Host port: `8080`

- Staging Service `nodePort`: `30081`
- Kind `containerPort`: `30081`
- Host port: `8081`

The mapping is bound to `127.0.0.1`, which limits exposure to the local machine. Binding to all interfaces would increase the attack surface and is unnecessary for this lab.

---

## Create and Validate the Cluster

Create the cluster from the repository root:

```bash
kind create cluster \
  --name pulumi-lab \
  --config cluster/kind-config.yaml
```

Kind normally creates the kubeconfig context `kind-pulumi-lab`.

Verify the context and API server:

```bash
kubectl config get-contexts
kubectl config current-context
kubectl cluster-info --context kind-pulumi-lab
kubectl get nodes --context kind-pulumi-lab -o wide
```

Inspect the Docker node and system Pods:

```bash
docker ps --filter name=pulumi-lab
kubectl get pods -n kube-system --context kind-pulumi-lab
```

Do not start the Pulumi deployment until the node is `Ready` and core system Pods are healthy. Otherwise, provider errors can be mistaken for program errors.

---

## Create the Pulumi Project

```bash
cd infra
pulumi login --local
pulumi new typescript
npm install @pulumi/kubernetes
```

Use a project name such as `pulumi-k8s-lab` and create a `dev` stack.

Expected structure:

```text
infra/
├── Pulumi.yaml
├── Pulumi.dev.yaml
├── index.ts
├── package.json
├── package-lock.json
├── tsconfig.json
└── node_modules/
```

A local backend is acceptable for an isolated lab. Team environments require secure shared state, access control, locking, backup, and recovery.

---

## Configure the Development Stack

```bash
pulumi stack select dev
pulumi config set kubeContext kind-pulumi-lab
pulumi config set replicas 2
pulumi config set image nginx:1.27-alpine
pulumi config set contentVersion v1
pulumi config set nodePort 30080
pulumi config set hostPort 8080
pulumi config
```

Configuration responsibilities:

- `kubeContext` identifies the target cluster context.
- `replicas` controls desired Pod count.
- `image` controls the container image.
- `contentVersion` is written to the Pod template to trigger a rollout when ConfigMap content changes.
- `nodePort` must match the Kind node port mapping.
- `hostPort` is used to publish a correct stack output for local access.

`hostPort` does not configure Kubernetes. It documents the external host endpoint created by the Kind mapping. `nodePort` is the Kubernetes Service property.

---

## Complete Pulumi Program

Replace `infra/index.ts` with:

```typescript
import * as pulumi from "@pulumi/pulumi";
import * as k8s from "@pulumi/kubernetes";

const stack = pulumi.getStack();
const config = new pulumi.Config();

const kubeContext = config.get("kubeContext") ?? "kind-pulumi-lab";
const replicas = config.getNumber("replicas") ?? 2;
const image = config.get("image") ?? "nginx:1.27-alpine";
const contentVersion = config.get("contentVersion") ?? "v1";
const nodePort = config.getNumber("nodePort") ?? 30080;
const hostPort = config.getNumber("hostPort") ?? 8080;

const provider = new k8s.Provider("kind-provider", {
    context: kubeContext,
});

const namespace = new k8s.core.v1.Namespace("demo-namespace", {
    metadata: {
        name: `pulumi-k8s-${stack}`,
        labels: {
            "app.kubernetes.io/managed-by": "pulumi",
            "app.kubernetes.io/part-of": "pulumi-k8s-lab",
        },
    },
}, { provider });

const appLabels = {
    "app.kubernetes.io/name": "pulumi-nginx",
    "app.kubernetes.io/instance": stack,
};

const webContent = new k8s.core.v1.ConfigMap("web-content", {
    metadata: {
        name: "pulumi-nginx-content",
        namespace: namespace.metadata.name,
    },
    data: {
        "index.html": `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Pulumi + Kubernetes</title>
</head>
<body>
  <h1>Pulumi manages this Kubernetes application</h1>
  <p>Stack: ${stack}</p>
  <p>Content version: ${contentVersion}</p>
</body>
</html>`,
    },
}, { provider });

const deployment = new k8s.apps.v1.Deployment("nginx-deployment", {
    metadata: {
        name: "pulumi-nginx",
        namespace: namespace.metadata.name,
        labels: appLabels,
    },
    spec: {
        replicas,
        selector: {
            matchLabels: appLabels,
        },
        strategy: {
            type: "RollingUpdate",
            rollingUpdate: {
                maxSurge: 1,
                maxUnavailable: 0,
            },
        },
        template: {
            metadata: {
                labels: appLabels,
                annotations: {
                    "demo.pulumi.com/content-version": contentVersion,
                },
            },
            spec: {
                containers: [{
                    name: "nginx",
                    image,
                    imagePullPolicy: "IfNotPresent",
                    ports: [{
                        name: "http",
                        containerPort: 80,
                    }],
                    resources: {
                        requests: {
                            cpu: "50m",
                            memory: "64Mi",
                        },
                        limits: {
                            cpu: "200m",
                            memory: "128Mi",
                        },
                    },
                    readinessProbe: {
                        httpGet: {
                            path: "/",
                            port: "http",
                        },
                        initialDelaySeconds: 2,
                        periodSeconds: 5,
                    },
                    livenessProbe: {
                        httpGet: {
                            path: "/",
                            port: "http",
                        },
                        initialDelaySeconds: 10,
                        periodSeconds: 10,
                    },
                    volumeMounts: [{
                        name: "web-content",
                        mountPath: "/usr/share/nginx/html",
                        readOnly: true,
                    }],
                }],
                volumes: [{
                    name: "web-content",
                    configMap: {
                        name: webContent.metadata.name,
                    },
                }],
            },
        },
    },
}, {
    provider,
    dependsOn: [webContent],
});

const service = new k8s.core.v1.Service("nginx-service", {
    metadata: {
        name: "pulumi-nginx",
        namespace: namespace.metadata.name,
        labels: appLabels,
    },
    spec: {
        type: "NodePort",
        selector: appLabels,
        ports: [{
            name: "http",
            port: 80,
            targetPort: "http",
            nodePort,
        }],
    },
}, {
    provider,
    dependsOn: [deployment],
});

export const namespaceName = namespace.metadata.name;
export const deploymentName = deployment.metadata.name;
export const serviceName = service.metadata.name;
export const desiredReplicas = replicas;
export const localUrl = `http://localhost:${hostPort}`;
```

---

## Program Analysis

### Imports, stack, and configuration

```typescript
import * as pulumi from "@pulumi/pulumi";
import * as k8s from "@pulumi/kubernetes";

const stack = pulumi.getStack();
const config = new pulumi.Config();
```

The active stack becomes part of namespace and label identity. Configuration separates environment-specific values from resource logic.

### Explicit provider and destination safety

```typescript
const provider = new k8s.Provider("kind-provider", {
    context: kubeContext,
});
```

Without an explicit provider, the Kubernetes package can use the current kubeconfig context. That is convenient but dangerous on a workstation connected to several clusters. An explicit provider makes the intended destination visible in code and stack configuration.

The context still must exist in kubeconfig. A provider does not create the cluster or invent credentials.

### Stack-specific namespace

```typescript
const namespace = new k8s.core.v1.Namespace("demo-namespace", {
    metadata: {
        name: `pulumi-k8s-${stack}`,
        labels: {
            "app.kubernetes.io/managed-by": "pulumi",
            "app.kubernetes.io/part-of": "pulumi-k8s-lab",
        },
    },
}, { provider });
```

The Pulumi logical name is `demo-namespace`. The Kubernetes physical name is `pulumi-k8s-dev` or `pulumi-k8s-staging`. The Pulumi URN is a third identity used by Pulumi state.

Separate namespaces reduce collisions and create a clear operational boundary. A namespace is not a complete security boundary by itself; production isolation can also require RBAC, NetworkPolicy, quotas, separate clusters, or separate cloud accounts.

### Labels and selectors

```typescript
const appLabels = {
    "app.kubernetes.io/name": "pulumi-nginx",
    "app.kubernetes.io/instance": stack,
};
```

The same label set is used by:

- Deployment metadata
- Pod template metadata
- Deployment selector
- Service selector

The Deployment selector must match the Pod template labels. The Service selector must match the Pods that should receive traffic. A typo can produce Running Pods with no Service endpoints.

### ConfigMap

The ConfigMap stores `index.html` separately from the Nginx image. This demonstrates configuration/content injection without building a custom image.

```typescript
const webContent = new k8s.core.v1.ConfigMap("web-content", {
    metadata: {
        name: "pulumi-nginx-content",
        namespace: namespace.metadata.name,
    },
    data: {
        "index.html": "...",
    },
}, { provider });
```

ConfigMaps are not secret stores. Sensitive values belong in Kubernetes Secrets or, preferably, a dedicated external secret system with an appropriate integration model.

### Deployment desired state

The Deployment specifies the number of replicas, selector, rollout strategy, and Pod template.

```typescript
spec: {
    replicas,
    selector: {
        matchLabels: appLabels,
    },
    strategy: {
        type: "RollingUpdate",
        rollingUpdate: {
            maxSurge: 1,
            maxUnavailable: 0,
        },
    },
    template: { /* Pod template */ },
}
```

`maxSurge: 1` permits one extra Pod during rollout. `maxUnavailable: 0` requests that no desired replica be unavailable during the update. The cluster still needs enough capacity to schedule the additional Pod.

### Pod-template annotation and ConfigMap rollout

```typescript
annotations: {
    "demo.pulumi.com/content-version": contentVersion,
},
```

Updating a ConfigMap object does not automatically guarantee that existing Pods restart. ConfigMap-backed volumes may update eventually, but many applications read configuration only at startup, and a rollout is often operationally clearer.

Placing `contentVersion` in the Pod-template annotation changes the template hash when the value changes. Kubernetes then creates a new ReplicaSet and performs a rolling update.

A production implementation can use a hash of the actual configuration content instead of a manually incremented version.

### Container port and resources

```typescript
ports: [{
    name: "http",
    containerPort: 80,
}],
resources: {
    requests: {
        cpu: "50m",
        memory: "64Mi",
    },
    limits: {
        cpu: "200m",
        memory: "128Mi",
    },
},
```

Requests influence scheduling and reserve capacity for planning. Limits constrain resource consumption. Poor values can cause unschedulable Pods, CPU throttling, or out-of-memory termination.

The named port `http` lets probes and Services refer to the port semantically rather than repeating `80`.

### Readiness and liveness

Readiness asks whether the Pod should receive traffic. Liveness asks whether the container should be restarted.

```typescript
readinessProbe: {
    httpGet: {
        path: "/",
        port: "http",
    },
    initialDelaySeconds: 2,
    periodSeconds: 5,
},
livenessProbe: {
    httpGet: {
        path: "/",
        port: "http",
    },
    initialDelaySeconds: 10,
    periodSeconds: 10,
},
```

A failed readiness probe removes the Pod from Service endpoints. A failed liveness probe can restart the container. A slow-starting application may also require a startup probe to prevent liveness checks from killing it before initialization completes.

### ConfigMap volume

```typescript
volumeMounts: [{
    name: "web-content",
    mountPath: "/usr/share/nginx/html",
    readOnly: true,
}],
volumes: [{
    name: "web-content",
    configMap: {
        name: webContent.metadata.name,
    },
}],
```

The ConfigMap becomes files in a volume. Mounting the volume at `/usr/share/nginx/html` replaces the content served by Nginx.

The reference to `webContent.metadata.name` creates a dependency. `dependsOn: [webContent]` also makes the operational relationship explicit, although the output reference already communicates a dependency.

### NodePort Service

```typescript
spec: {
    type: "NodePort",
    selector: appLabels,
    ports: [{
        name: "http",
        port: 80,
        targetPort: "http",
        nodePort,
    }],
},
```

- `port` is the Service port inside the cluster.
- `targetPort` sends traffic to the named container port.
- `nodePort` opens a fixed port on each Kubernetes node.
- The Kind configuration forwards a host port to that node port.

NodePort is used here to make host access explicit. In production, a `LoadBalancer`, Ingress, Gateway API resource, or internal `ClusterIP` with another exposure layer is more common.

### Stack outputs

```typescript
export const namespaceName = namespace.metadata.name;
export const deploymentName = deployment.metadata.name;
export const serviceName = service.metadata.name;
export const desiredReplicas = replicas;
export const localUrl = `http://localhost:${hostPort}`;
```

Outputs are a stable stack contract. They can be read by humans, CI pipelines, or another stack.

---

## Type Check Before Deployment

```bash
npx tsc --noEmit
```

This catches TypeScript errors without generating JavaScript files. It does not validate cluster connectivity or guarantee that every Kubernetes value is operationally correct, but it shortens the feedback loop.

---

## Preview and Deploy

Preview:

```bash
pulumi preview
```

Review the target stack, provider, namespace, resource names, replicas, NodePort, image, creates, replacements, and deletes.

Deploy:

```bash
pulumi up
```

Pulumi submits objects through the Kubernetes provider. Kubernetes then creates ReplicaSets, Pods, endpoints, and other controller-owned objects that are not declared as separate Pulumi resources.

Read outputs and URNs:

```bash
pulumi stack output
pulumi stack output localUrl
pulumi stack --show-urns
```

---

## Validate with kubectl

Inspect the namespace and resources:

```bash
kubectl get namespace pulumi-k8s-dev
kubectl get all -n pulumi-k8s-dev
kubectl get configmap -n pulumi-k8s-dev
kubectl get endpointslice -n pulumi-k8s-dev
```

Wait for the Deployment:

```bash
kubectl rollout status deployment/pulumi-nginx \
  -n pulumi-k8s-dev

kubectl get pods \
  -n pulumi-k8s-dev \
  -l app.kubernetes.io/name=pulumi-nginx \
  -o wide
```

Access the application:

```bash
curl http://localhost:8080
```

Or open:

```text
http://localhost:8080
```

Inspect logs and object details:

```bash
kubectl logs -n pulumi-k8s-dev \
  -l app.kubernetes.io/name=pulumi-nginx \
  --tail=50

kubectl describe deployment pulumi-nginx -n pulumi-k8s-dev
kubectl describe service pulumi-nginx -n pulumi-k8s-dev
```

Pulumi output confirms the intended managed resources. `kubectl` confirms live cluster behavior. Both views are required during troubleshooting.

---

## Scale the Deployment

Change development from two replicas to four:

```bash
pulumi config set replicas 4
pulumi preview
pulumi up
```

Verify:

```bash
kubectl get deployment pulumi-nginx -n pulumi-k8s-dev
kubectl get pods -n pulumi-k8s-dev \
  -l app.kubernetes.io/name=pulumi-nginx
```

The Deployment object is updated in place. The Kubernetes Deployment controller creates additional Pods. Pulumi does not directly create each Pod because the Deployment owns that runtime behavior.

---

## Change the Image and Observe a Rolling Update

```bash
pulumi config set image nginx:alpine
pulumi preview
pulumi up

kubectl rollout status deployment/pulumi-nginx \
  -n pulumi-k8s-dev

kubectl rollout history deployment/pulumi-nginx \
  -n pulumi-k8s-dev
```

Changing the container image changes the Pod template. Kubernetes creates a new ReplicaSet and gradually replaces Pods according to the rolling-update strategy.

For production reproducibility, pin a controlled image version or digest. Mutable tags can point to different images without a source-code change.

---

## Change the Web Content

Update the version that appears in the Pod template:

```bash
pulumi config set contentVersion v2
pulumi preview
pulumi up

kubectl rollout status deployment/pulumi-nginx \
  -n pulumi-k8s-dev

curl http://localhost:8080
```

The ConfigMap data changes, and the Pod-template annotation changes. The annotation change guarantees a Deployment rollout.

For a detailed property-level preview:

```bash
pulumi preview --diff
```

---

## Introduce and Reconcile Drift

Manually scale the live Deployment to six replicas:

```bash
kubectl scale deployment pulumi-nginx \
  -n pulumi-k8s-dev \
  --replicas=6

kubectl get deployment pulumi-nginx -n pulumi-k8s-dev
```

The Pulumi program still declares four replicas. The live cluster now differs from the desired program.

Refresh the Pulumi checkpoint and review the plan:

```bash
pulumi refresh
pulumi preview
```

Restore the declared state:

```bash
pulumi up
kubectl get deployment pulumi-nginx -n pulumi-k8s-dev
```

### Drift caused by external deletion

In this lab only, delete the Service outside Pulumi:

```bash
kubectl delete service pulumi-nginx -n pulumi-k8s-dev
pulumi refresh
pulumi preview
pulumi up
```

Pulumi should recreate the missing Service.

Refresh records live state; update enforces the program. Neither command decides whether an emergency manual change is valid. Operators must choose whether to remediate or adopt the change.

---

## Create a Staging Stack

Create independent staging configuration:

```bash
pulumi stack init staging
pulumi stack select staging

pulumi config set kubeContext kind-pulumi-lab
pulumi config set replicas 1
pulumi config set image nginx:1.27-alpine
pulumi config set contentVersion staging-v1
pulumi config set nodePort 30081
pulumi config set hostPort 8081

pulumi preview
pulumi up
```

The source program creates namespace `pulumi-k8s-staging` because it includes the stack name. The NodePort and host mapping are also different.

Verify both environments:

```bash
kubectl get namespaces | grep pulumi-k8s
kubectl get all -n pulumi-k8s-dev
kubectl get all -n pulumi-k8s-staging

curl http://localhost:8080
curl http://localhost:8081

pulumi stack ls
```

Return to development:

```bash
pulumi stack select dev
pulumi stack output localUrl
pulumi config
```

A stack is not just an `environment` variable. It is an independent state, configuration, output, and resource-management boundary.

---

## Pulumi State and Kubernetes State

Pulumi and Kubernetes both use desired-state concepts, but they operate at different layers.

### Pulumi state

Pulumi records the Kubernetes resources that the program owns, their inputs, outputs, URNs, dependencies, and provider references.

### Kubernetes API state

The Kubernetes API server stores cluster objects such as Namespaces, ConfigMaps, Deployments, ReplicaSets, Pods, and Services. Controllers continuously reconcile objects such as Deployments into lower-level runtime objects.

### Example

Pulumi declares one Deployment. Kubernetes creates one or more ReplicaSets and Pods. Those controller-generated Pods are not separate top-level Pulumi resources because Pulumi manages the Deployment abstraction, not every controller-owned child object.

### Server-side apply and field ownership

Kubernetes supports multiple field managers. Pulumi's provider must coexist with controllers and possibly other tools. Unexpected conflicts can occur when several systems attempt to own the same fields. Avoid mixing `kubectl apply`, Helm, GitOps controllers, and Pulumi ownership of the same object unless the field-ownership and import strategy is deliberately designed.

### Why Pulumi does not delete every YAML object in the cluster

Pulumi destroys resources that belong to the selected stack. It does not treat the entire cluster as its exclusive desired state. Unmanaged namespaces, controller-generated Pods, system resources, and objects managed by other stacks or tools are outside that stack's ownership.

---

## Implicit and Explicit Dependencies

Many dependencies are implicit:

- Namespace name output is used by namespaced resources.
- ConfigMap name output is used by the Pod volume.
- Deployment and Service use the same labels.

Explicit `dependsOn` is useful when a real operational dependency is not expressed through an input/output reference. Avoid adding it to every resource because unnecessary dependencies reduce parallelism and can hide weak modeling.

---

## Logical Names, Kubernetes Names, and URNs

Each resource can have three different identities:

1. **Pulumi logical name** — for example, `nginx-deployment`
2. **Kubernetes physical name** — for example, `pulumi-nginx`
3. **Pulumi URN** — a state identity containing stack, project, type, and logical name

Changing a Kubernetes metadata name can replace an object. Changing a Pulumi logical name can appear as delete/create unless aliases or a state migration are used. Refactoring names is therefore a lifecycle operation, not merely cosmetic editing.

---

## Troubleshooting

Use a layered workflow:

1. Docker and Kind
2. kubeconfig and context
3. Kubernetes API connectivity
4. Pulumi project and active stack
5. Provider configuration
6. Object specification
7. Controller status
8. Pod events, logs, and probes
9. Service selectors and endpoints
10. Host-to-node port mapping

### Kubernetes context not found

```bash
kubectl config get-contexts
kubectl config view
pulumi config get kubeContext
```

Confirm that `kind-pulumi-lab` exists and that the stack value exactly matches it. The explicit provider fails if the configured context is missing.

### Connection refused or cluster unreachable

```bash
docker ps --filter name=pulumi-lab
kind get clusters
kubectl cluster-info --context kind-pulumi-lab
```

If the Kind container is absent, recreate the cluster. If kubeconfig points to an obsolete endpoint, regenerate or repair the context.

### `localhost:8080` does not respond

Inspect every hop:

```bash
kubectl get service pulumi-nginx -n pulumi-k8s-dev -o yaml
kubectl get endpointslice -n pulumi-k8s-dev
kubectl get pods -n pulumi-k8s-dev -o wide
curl -v http://localhost:8080
```

Confirm:

- The Service is `NodePort`.
- `nodePort` is `30080`.
- The Kind mapping forwards host `8080` to node `30080`.
- EndpointSlices contain Ready Pod addresses.
- Service selectors match Pod labels.

Use port-forward as a diagnostic bypass:

```bash
kubectl port-forward \
  -n pulumi-k8s-dev \
  service/pulumi-nginx \
  8088:80
```

If `http://localhost:8088` works, the application and Service are probably healthy and the problem is in the NodePort/Kind host mapping.

### Port already allocated or NodePort conflict

```bash
kubectl get services -A

# Linux or macOS example
lsof -i :8080
```

A host port can be occupied by another process. A NodePort can already be assigned to another Service. Select unused values and keep Kind configuration and stack configuration aligned.

### `ImagePullBackOff`

```bash
kubectl describe pod -n pulumi-k8s-dev <pod-name>
kubectl get events -n pulumi-k8s-dev \
  --sort-by=.metadata.creationTimestamp
```

Check image spelling, tag existence, registry access, proxy/DNS, rate limits, and image-pull credentials.

### Pod is Running but not Ready

```bash
kubectl describe pod -n pulumi-k8s-dev <pod-name>
kubectl logs -n pulumi-k8s-dev <pod-name>
kubectl exec -n pulumi-k8s-dev <pod-name> -- \
  wget -qO- http://127.0.0.1/
```

Check readiness path, named port, startup timing, mounted content, Nginx configuration, and events.

### Update waits or times out

```bash
kubectl get pods -n pulumi-k8s-dev -w
kubectl describe deployment pulumi-nginx -n pulumi-k8s-dev
kubectl get events -n pulumi-k8s-dev \
  --sort-by=.lastTimestamp
```

Common causes include insufficient capacity for `maxSurge`, failed readiness probes, image pulls, resource limits, and unschedulable Pods.

### ConfigMap changed but Pods did not restart

A ConfigMap change alone is not a Deployment template change. Increment `contentVersion`, or compute and apply a content checksum to the Pod-template annotation.

### Unexpected replacement or deletion in preview

Check:

- Active stack
- Kubernetes context
- Logical resource-name changes
- Metadata name changes
- Namespace changes
- Immutable Kubernetes fields
- Provider version changes
- Resource import/ownership changes

Do not approve a replacement until its operational impact is understood.

---

## Clean Up

Destroy staging:

```bash
pulumi stack select staging
pulumi destroy
pulumi stack rm staging
```

Destroy development:

```bash
pulumi stack select dev
pulumi destroy
pulumi stack rm dev
```

Confirm that stack-managed namespaces are gone:

```bash
kubectl get namespaces | grep pulumi-k8s || true
```

Then delete the cluster:

```bash
cd ..
kind delete cluster --name pulumi-lab
kind get clusters
kubectl config get-contexts
```

Destroy application resources before deleting the cluster. If the cluster is deleted first, Pulumi cannot reach the API server to perform ordinary deletions, and the stack can retain stale resource state that requires recovery work.

---

## Exercises

### Add an environment variable

Create an environment value in Pulumi configuration:

```bash
pulumi config set environmentName development
```

Read it in TypeScript and pass it to the container using `env`.

### Add a startup probe

Add a startup probe so a slow application is protected from premature liveness failure.

### Add a ResourceQuota

Create a `core.v1.ResourceQuota` in each stack namespace to constrain aggregate CPU, memory, and object counts.

### Add a ServiceAccount

Create a dedicated ServiceAccount, assign it to the Pod template, and set:

```typescript
automountServiceAccountToken: false
```

unless the workload genuinely requires Kubernetes API credentials.

### Replace NodePort with ClusterIP

Change the Service to `ClusterIP` and access it with:

```bash
kubectl port-forward -n pulumi-k8s-dev service/pulumi-nginx 8088:80
```

Explain why ClusterIP is safer as a default for internal services.

### Build a ComponentResource

Encapsulate Namespace, ConfigMap, Deployment, and Service in a reusable Pulumi component with typed arguments and registered outputs.

### Create a third stack

Add a `test` stack with a unique namespace, NodePort, and Kind host mapping. Explain every collision boundary.

### Add tests

Use Pulumi mocks to verify that:

- The Deployment has the required labels.
- Resource requests and limits exist.
- The Service selector matches the Pod labels.
- The namespace name contains the stack name.
- The container does not use an uncontrolled image tag.

---

## Review Questions

1. Why is an explicit Kubernetes provider safer than using the current context implicitly?
2. Why does the Service select Pods rather than the Deployment object?
3. What happens when a Deployment selector does not match its Pod-template labels?
4. Why can a ConfigMap update require a Pod-template checksum or version annotation?
5. How do readiness and liveness probes differ?
6. What is the operational effect of `maxUnavailable: 0`?
7. Why does a Pulumi Deployment resource produce Kubernetes Pods that are not separate Pulumi resources?
8. Why can `pulumi refresh` change recorded state without restoring desired state?
9. What must remain unique when multiple stacks share one Kind cluster?
10. Why should the application stacks be destroyed before the cluster?

---

## Key Takeaways

- Pulumi creates Kubernetes API objects; Kubernetes controllers operate those objects continuously.
- An explicit provider makes cluster targeting deliberate and reviewable.
- Stack-specific namespaces and configuration enable one program to manage multiple environments.
- Labels and selectors are the logical wiring between Deployment Pods and Services.
- ConfigMaps separate content from images, but they are not secret stores.
- Resource requests, limits, and probes are part of production-quality workload design.
- Kind host mapping and Kubernetes NodePort configuration must match exactly.
- Scaling and image changes demonstrate declarative updates and Kubernetes rolling reconciliation.
- Refresh observes live state; update moves resources toward the program's desired state.
- Pulumi state, Kubernetes API state, and controller-generated runtime objects are related but distinct.
- Cleanup order matters because stateful tools need access to the target API to delete managed resources cleanly.

---

## Official References

- Pulumi Kubernetes Provider: <https://www.pulumi.com/registry/packages/kubernetes/>
- Kubernetes Provider Configuration: <https://www.pulumi.com/registry/packages/kubernetes/installation-configuration/>
- Pulumi Kubernetes Examples: <https://www.pulumi.com/registry/packages/kubernetes/how-to-guides/>
- Kind Documentation: <https://kind.sigs.k8s.io/>
- Kind Configuration: <https://kind.sigs.k8s.io/docs/user/configuration/>
- Kubernetes Deployments: <https://kubernetes.io/docs/concepts/workloads/controllers/deployment/>
- Kubernetes Services: <https://kubernetes.io/docs/concepts/services-networking/service/>
- ConfigMaps: <https://kubernetes.io/docs/concepts/configuration/configmap/>
- Probes: <https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/>
- Resource Management: <https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/>
- Pulumi Drift Detection: <https://www.pulumi.com/docs/deployments/deployments/drift/>

> Kubernetes APIs, provider behavior, and container image versions evolve. Validate the code and commands against the versions used by your repository before applying the design to a production cluster.
