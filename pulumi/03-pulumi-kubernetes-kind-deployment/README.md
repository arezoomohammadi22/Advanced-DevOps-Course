# Pulumi Kubernetes Multi-Stack Deployment

Deploy one Kubernetes application into two isolated namespaces by using a single Pulumi YAML program and two independent Pulumi stacks.

The project demonstrates how a shared infrastructure definition can manage multiple environments without duplicating the program. The `dev` and `staging` stacks use the same `Pulumi.yaml`, but each stack has its own configuration, state, Kubernetes namespace, resource policy, and lifecycle.

---

## Table of Contents

- [Architecture](#architecture)
- [What This Project Teaches](#what-this-project-teaches)
- [Environment Design](#environment-design)
- [Pulumi Stack Versus Kubernetes Namespace](#pulumi-stack-versus-kubernetes-namespace)
- [Execution and State Flows](#execution-and-state-flows)
- [Prerequisites](#prerequisites)
- [Verify the Kubernetes Context and Permissions](#verify-the-kubernetes-context-and-permissions)
- [Verify the Pulumi Backend](#verify-the-pulumi-backend)
- [Create the Project](#create-the-project)
- [Repository Layout](#repository-layout)
- [Project Files](#project-files)
  - [`Pulumi.yaml`](#pulumiyaml)
  - [`Pulumi.dev.yaml`](#pulumidevyaml)
  - [`Pulumi.staging.yaml`](#pulumistagingyaml)
  - [`.gitignore`](#gitignore)
- [Create and Configure the Stacks](#create-and-configure-the-stacks)
- [Preview and Deploy Development](#preview-and-deploy-development)
- [Validate Development](#validate-development)
- [Preview and Deploy Staging](#preview-and-deploy-staging)
- [Validate Staging](#validate-staging)
- [Prove Stack Independence](#prove-stack-independence)
- [Inspect Stack State](#inspect-stack-state)
- [Update Only Development](#update-only-development)
- [Trigger a Rolling Update in Staging](#trigger-a-rolling-update-in-staging)
- [Drift Detection and Recovery](#drift-detection-and-recovery)
- [Why Deleting a Pod Is Usually Not Persistent Pulumi Drift](#why-deleting-a-pod-is-usually-not-persistent-pulumi-drift)
- [Provider and Namespace Behavior](#provider-and-namespace-behavior)
- [Dependency Graph](#dependency-graph)
- [What Namespace Isolation Does and Does Not Provide](#what-namespace-isolation-does-and-does-not-provide)
- [Optional Resource Protection](#optional-resource-protection)
- [Troubleshooting](#troubleshooting)
- [Cleanup](#cleanup)
- [Production Considerations](#production-considerations)
- [Exercises](#exercises)
- [Final Verification Checklist](#final-verification-checklist)
- [Official References](#official-references)

---

## Architecture

```text
One Pulumi Project
        │
        ├── Shared Pulumi.yaml program
        │
        ├── Stack: dev
        │     ├── Pulumi.dev.yaml
        │     ├── Independent state checkpoint
        │     └── Kubernetes namespace: pulumi-dev
        │
        └── Stack: staging
              ├── Pulumi.staging.yaml
              ├── Independent state checkpoint
              └── Kubernetes namespace: pulumi-staging
```

Each stack creates the following resources:

```text
Namespace
├── ResourceQuota
├── ConfigMap
├── Deployment
│   └── ReplicaSet
│       └── Pod(s)
└── ClusterIP Service
    └── EndpointSlice
```

The application is an Nginx web service. Its `index.html` file is provided by a ConfigMap and contains environment-specific values such as the active Pulumi stack, namespace, and message.

---

## What This Project Teaches

This lab covers the following concepts:

- One shared Pulumi YAML program for multiple environments.
- Independent `dev` and `staging` stacks.
- Independent configuration and state per stack.
- One Kubernetes namespace per environment.
- An explicit Kubernetes provider with a stack-specific default namespace.
- Built-in Pulumi YAML variables such as `${pulumi.stack}`.
- Stack configuration with strongly typed integer and string values.
- Kubernetes Namespace, ResourceQuota, ConfigMap, Deployment, and Service resources.
- Deployment selectors, pod labels, RollingUpdate behavior, and health probes.
- CPU and memory requests and limits.
- ConfigMap volumes mounted into Nginx.
- Implicit and explicit Pulumi dependencies.
- Stack outputs for operational commands and service discovery.
- Independent updates and destruction of environments.
- Pulumi drift detection, remediation, and adoption.
- The difference between Pulumi reconciliation and Kubernetes controller reconciliation.

---

## Environment Design

| Setting | `dev` | `staging` |
|---|---:|---:|
| Kubernetes namespace | `pulumi-dev` | `pulumi-staging` |
| Initial replicas | `1` | `2` |
| Local port-forward port | `8081` | `8082` |
| Pod quota | `10` | `20` |
| CPU request | `50m` | `100m` |
| CPU limit | `250m` | `500m` |
| Memory request | `64Mi` | `128Mi` |
| Memory limit | `128Mi` | `256Mi` |
| Environment message | Development environment | Staging environment |

Both environments use the same Kubernetes resource names, such as `multi-stack-web`. This is valid because namespaced resources are identified by both their namespace and name.

```text
pulumi-dev/multi-stack-web
pulumi-staging/multi-stack-web
```

---

## Pulumi Stack Versus Kubernetes Namespace

A Pulumi stack and a Kubernetes namespace solve different problems.

### Pulumi stack

A stack is an independently configurable instance of a Pulumi program. Each stack has:

- its own configuration;
- its own state checkpoint;
- its own resource URNs;
- its own update history;
- an independent lifecycle.

### Kubernetes namespace

A namespace is a Kubernetes scope for namespaced resources. It helps organize resources and permits identical names in different namespaces.

In this project, each Pulumi stack is intentionally mapped to one Kubernetes namespace:

```text
Pulumi stack dev      → Kubernetes namespace pulumi-dev
Pulumi stack staging  → Kubernetes namespace pulumi-staging
```

The mapping is a design decision. A namespace does not replace a stack, and a stack does not replace a namespace.

> **Ownership rule:** Two independent stacks must not manage the same physical namespace or the same physical Kubernetes resource. Every resource must have one clear Pulumi owner.

---

## Execution and State Flows

Pulumi uses two independent paths during an update.

### State path

```text
Pulumi CLI
    ↓
Pulumi Engine
    ↓
Active Backend
    ↓
Selected Stack State
```

The backend may be Pulumi Cloud, a local backend, PostgreSQL, S3-compatible storage, or another supported backend. The backend stores Pulumi state; it does not create Kubernetes resources.

### Infrastructure path

```text
Pulumi YAML Program
    ↓
Pulumi YAML Runtime
    ↓
Pulumi Engine
    ↓
Kubernetes Provider
    ↓
Kubernetes API Server
    ↓
Kubernetes Controllers
    ↓
ReplicaSet and Pods
```

When Pulumi creates a Deployment, Pulumi manages the Deployment object. Kubernetes controllers create and reconcile its ReplicaSet and Pods.

---

## Prerequisites

The following tools and access are required:

- Pulumi CLI.
- `kubectl`.
- Access to a Kubernetes cluster.
- A valid kubeconfig.
- Permission to create namespaces, deployments, services, ConfigMaps, and ResourceQuotas.
- A configured Pulumi backend.
- Optional: `jq` for inspecting exported state.
- Optional: `curl` for HTTP validation.

The Kubernetes cluster may be Minikube, kind, K3s, an on-premises cluster, or a managed Kubernetes service.

Check the installed tools and cluster:

```bash
pulumi version
kubectl version --client
kubectl config current-context
kubectl cluster-info
kubectl get nodes
```

Expected result:

- Pulumi prints its installed version.
- `kubectl` prints the current context.
- `kubectl cluster-info` reaches the API server.
- Nodes appear in a healthy state, normally `Ready`.

If `kubectl` cannot access the cluster, the Pulumi Kubernetes provider will not be able to access it through the default kubeconfig configuration either.

---

## Verify the Kubernetes Context and Permissions

Display the kubeconfig path used by the current shell:

```bash
echo "${KUBECONFIG:-$HOME/.kube/config}"
```

Inspect the active context only:

```bash
kubectl config view --minify
```

Check the required permissions:

```bash
kubectl auth can-i create namespaces
kubectl auth can-i create deployments.apps --all-namespaces
kubectl auth can-i create services --all-namespaces
kubectl auth can-i create configmaps --all-namespaces
kubectl auth can-i create resourcequotas --all-namespaces
```

The expected result for each command is:

```text
yes
```

If namespace creation is restricted, a cluster administrator can pre-create the namespaces. In that model, either import the existing namespaces into Pulumi or move namespace ownership to a separate platform stack. Do not allow two stacks to claim ownership of the same existing namespace.

> Namespace separation alone is not complete security isolation. Production isolation commonly also requires RBAC, NetworkPolicy, ResourceQuota, LimitRange, and possibly separate nodes, runtimes, clusters, or cloud accounts.

---

## Verify the Pulumi Backend

Check the active backend and existing stacks:

```bash
pulumi whoami -v
pulumi stack ls
```

The stack state and Kubernetes resources are managed through different paths:

```text
Pulumi Engine → Backend → Stack State
Pulumi Engine → Kubernetes Provider → Kubernetes API Server
```

If you use a PostgreSQL backend running inside Kubernetes, make sure its database connection or port-forward is active before running Pulumi commands.

> Avoid storing the backend for a critical cluster only inside that same cluster. A cluster outage could make both the workloads and the state backend unavailable at the same time.

---

## Create the Project

Create the project directory:

```bash
mkdir -p ~/pulumi-kubernetes-multi-stack
cd ~/pulumi-kubernetes-multi-stack
```

Initialize a Pulumi YAML project:

```bash
pulumi new yaml
```

Use the following project name when prompted:

```text
pulumi-kubernetes-multi-stack
```

If the wizard creates an initial stack, it may be named `dev`. Otherwise, create both stacks explicitly in the next steps.

---

## Repository Layout

```text
pulumi-kubernetes-multi-stack/
├── Pulumi.yaml
├── Pulumi.dev.yaml
├── Pulumi.staging.yaml
└── .gitignore
```

- `Pulumi.yaml` is the shared infrastructure program.
- `Pulumi.dev.yaml` contains settings for the `dev` stack.
- `Pulumi.staging.yaml` contains settings for the `staging` stack.
- Stack settings files are not state files.
- State is stored in the active Pulumi backend.
- Non-sensitive stack settings may be committed to Git.
- Sensitive values must be set with `pulumi config set --secret` or supplied through an external secret-management workflow.

---

## Project Files

### `Pulumi.yaml`

Create the following file in the project root:

```yaml
name: pulumi-kubernetes-multi-stack
runtime: yaml
description: Deploy the same Kubernetes application into isolated namespaces by using independent Pulumi stacks

config:
  namespaceName:
    type: string
  replicas:
    type: integer
    default: 1
  image:
    type: string
    default: nginx:1.27-alpine
  environmentMessage:
    type: string
  localTestPort:
    type: integer
  podQuota:
    type: string
    default: "10"
  cpuRequest:
    type: string
    default: 50m
  memoryRequest:
    type: string
    default: 64Mi
  cpuLimit:
    type: string
    default: 250m
  memoryLimit:
    type: string
    default: 128Mi

variables:
  appLabels:
    app.kubernetes.io/name: multi-stack-web
    app.kubernetes.io/instance: ${pulumi.stack}
    app.kubernetes.io/managed-by: pulumi
    environment: ${pulumi.stack}

resources:
  k8sProvider:
    type: pulumi:providers:kubernetes
    properties:
      namespace: ${namespaceName}
    options:
      version: 4.32.0

  appNamespace:
    type: kubernetes:core/v1:Namespace
    properties:
      metadata:
        name: ${namespaceName}
        labels: ${appLabels}
    options:
      provider: ${k8sProvider}

  namespaceQuota:
    type: kubernetes:core/v1:ResourceQuota
    properties:
      metadata:
        name: application-quota
        labels: ${appLabels}
      spec:
        hard:
          pods: ${podQuota}
    options:
      provider: ${k8sProvider}
      dependsOn:
        - ${appNamespace}

  webContent:
    type: kubernetes:core/v1:ConfigMap
    properties:
      metadata:
        name: multi-stack-web-content
        labels: ${appLabels}
      data:
        index.html: |
          <!doctype html>
          <html lang="en">
          <head>
            <meta charset="utf-8">
            <title>Pulumi Kubernetes Multi-Stack Lab</title>
          </head>
          <body>
            <h1>Pulumi Kubernetes Multi-Stack Lab</h1>
            <p>Stack: ${pulumi.stack}</p>
            <p>Namespace: ${namespaceName}</p>
            <p>Message: ${environmentMessage}</p>
          </body>
          </html>
    options:
      provider: ${k8sProvider}
      dependsOn:
        - ${appNamespace}

  webDeployment:
    type: kubernetes:apps/v1:Deployment
    properties:
      metadata:
        name: multi-stack-web
        labels: ${appLabels}
      spec:
        replicas: ${replicas}
        strategy:
          type: RollingUpdate
          rollingUpdate:
            maxUnavailable: 0
            maxSurge: 1
        selector:
          matchLabels:
            app.kubernetes.io/name: multi-stack-web
            app.kubernetes.io/instance: ${pulumi.stack}
        template:
          metadata:
            labels: ${appLabels}
          spec:
            terminationGracePeriodSeconds: 10
            containers:
              - name: nginx
                image: ${image}
                imagePullPolicy: IfNotPresent
                ports:
                  - name: http
                    containerPort: 80
                    protocol: TCP
                resources:
                  requests:
                    cpu: ${cpuRequest}
                    memory: ${memoryRequest}
                  limits:
                    cpu: ${cpuLimit}
                    memory: ${memoryLimit}
                readinessProbe:
                  httpGet:
                    path: /
                    port: http
                  initialDelaySeconds: 2
                  periodSeconds: 5
                  timeoutSeconds: 2
                  failureThreshold: 3
                livenessProbe:
                  httpGet:
                    path: /
                    port: http
                  initialDelaySeconds: 10
                  periodSeconds: 10
                  timeoutSeconds: 2
                  failureThreshold: 3
                volumeMounts:
                  - name: web-content
                    mountPath: /usr/share/nginx/html
                    readOnly: true
            volumes:
              - name: web-content
                configMap:
                  name: ${webContent.metadata.name}
    options:
      provider: ${k8sProvider}
      dependsOn:
        - ${appNamespace}

  webService:
    type: kubernetes:core/v1:Service
    properties:
      metadata:
        name: multi-stack-web
        labels: ${appLabels}
      spec:
        type: ClusterIP
        selector:
          app.kubernetes.io/name: multi-stack-web
          app.kubernetes.io/instance: ${pulumi.stack}
        ports:
          - name: http
            protocol: TCP
            port: 80
            targetPort: http
    options:
      provider: ${k8sProvider}
      dependsOn:
        - ${appNamespace}

outputs:
  stackName: ${pulumi.stack}
  namespace: ${appNamespace.metadata.name}
  deploymentName: ${webDeployment.metadata.name}
  serviceName: ${webService.metadata.name}
  serviceDns: ${webService.metadata.name}.${namespaceName}.svc.cluster.local
  requestedReplicas: ${replicas}
  localTestPort: ${localTestPort}
  portForwardCommand: kubectl -n ${namespaceName} port-forward service/${webService.metadata.name} ${localTestPort}:80
  testUrl: http://127.0.0.1:${localTestPort}
```

### Important notes about `Pulumi.yaml`

#### Required and default configuration

`namespaceName`, `environmentMessage`, and `localTestPort` have no defaults and must be configured in every stack.

`replicas` is defined as an integer, so it remains a numeric value when assigned to `spec.replicas`.

CPU and memory values are strings because Kubernetes receives resource quantities such as `50m`, `64Mi`, and `128Mi` as quantity strings.

#### `localTestPort` is not a cluster resource

`localTestPort` is used only to generate a stack output containing the appropriate `kubectl port-forward` command. It does not create or reserve a port inside Kubernetes.

Both Services listen on port `80`. They do not conflict because they exist in different namespaces. Local port `8081` is used for `dev`, and local port `8082` is used for `staging` so both can be tested simultaneously.

#### Built-in variables

`${pulumi.stack}` resolves to the selected stack name during execution. It is used in labels, selectors, and the generated HTML page.

#### Explicit provider

The provider defines the default namespace for namespaced resources:

```yaml
k8sProvider:
  type: pulumi:providers:kubernetes
  properties:
    namespace: ${namespaceName}
```

Because no kubeconfig is specified directly, the provider reads `KUBECONFIG` or the default `~/.kube/config`.

Namespace selection follows this practical priority:

1. `metadata.namespace` set directly on a resource;
2. the default namespace configured on the provider;
3. the namespace from the active kubeconfig context.

This project intentionally omits `metadata.namespace` from namespaced resources to demonstrate provider-scoped namespace configuration.

#### Namespace resource

A Namespace is cluster-scoped. The provider's default namespace does not affect the Namespace resource itself. Its physical name comes directly from `${namespaceName}`.

#### ResourceQuota

The ResourceQuota limits the number of Pods in each namespace. It has an explicit dependency on the Namespace because there is no direct Namespace output used in its properties from which Pulumi could infer the dependency.

#### ConfigMap

The same ConfigMap name is used in both environments. This is valid because each ConfigMap exists in a different namespace.

The HTML content includes stack-specific values, making it easy to confirm which environment answered an HTTP request.

#### Deployment selector and pod labels

The Deployment selector must exactly match the labels on the pod template. A mismatch can cause Kubernetes to reject the Deployment or cause the Service to have no matching endpoints.

#### RollingUpdate

```yaml
maxUnavailable: 0
maxSurge: 1
```

This configuration allows Kubernetes to create an additional Pod before terminating an old Ready Pod during a pod-template update.

#### Resource requests and limits

Requests influence scheduling. Limits constrain resource consumption.

#### Readiness and liveness probes

- The readiness probe determines when a Pod may receive Service traffic.
- The liveness probe determines whether the container should be restarted.
- Pulumi does not execute these probes. Pulumi sends the Deployment specification to the API server, and the kubelet executes the probes.

#### ConfigMap volume dependency

The Deployment references `${webContent.metadata.name}`. This creates an implicit dependency from the Deployment to the ConfigMap.

#### Service and EndpointSlice

The ClusterIP Service selects Ready Pods using labels. `targetPort: http` refers to the named container port.

The full in-cluster DNS names are:

```text
multi-stack-web.pulumi-dev.svc.cluster.local
multi-stack-web.pulumi-staging.svc.cluster.local
```

---

### `Pulumi.dev.yaml`

The file is generated by `pulumi config set` commands. Its exact encryption metadata may differ if secret values are later added.

```yaml
config:
  pulumi-kubernetes-multi-stack:namespaceName: pulumi-dev
  pulumi-kubernetes-multi-stack:replicas: 1
  pulumi-kubernetes-multi-stack:image: nginx:1.27-alpine
  pulumi-kubernetes-multi-stack:environmentMessage: Development environment managed by Pulumi
  pulumi-kubernetes-multi-stack:localTestPort: 8081
  pulumi-kubernetes-multi-stack:podQuota: "10"
  pulumi-kubernetes-multi-stack:cpuRequest: 50m
  pulumi-kubernetes-multi-stack:memoryRequest: 64Mi
  pulumi-kubernetes-multi-stack:cpuLimit: 250m
  pulumi-kubernetes-multi-stack:memoryLimit: 128Mi
```

---

### `Pulumi.staging.yaml`

```yaml
config:
  pulumi-kubernetes-multi-stack:namespaceName: pulumi-staging
  pulumi-kubernetes-multi-stack:replicas: 2
  pulumi-kubernetes-multi-stack:image: nginx:1.27-alpine
  pulumi-kubernetes-multi-stack:environmentMessage: Staging environment managed by Pulumi
  pulumi-kubernetes-multi-stack:localTestPort: 8082
  pulumi-kubernetes-multi-stack:podQuota: "20"
  pulumi-kubernetes-multi-stack:cpuRequest: 100m
  pulumi-kubernetes-multi-stack:memoryRequest: 128Mi
  pulumi-kubernetes-multi-stack:cpuLimit: 500m
  pulumi-kubernetes-multi-stack:memoryLimit: 256Mi
```

---

### `.gitignore`

```gitignore
# Pulumi exported state files
*-state.json
*.state.json

# Local temporary files
*.tmp
*.log

# Local environment files
.env
.env.*

# Editor files
.vscode/
.idea/
*.swp

# OS files
.DS_Store
Thumbs.db
```

Do not ignore `Pulumi.dev.yaml` and `Pulumi.staging.yaml` when they contain only non-sensitive configuration. Secret values configured with `--secret` are encrypted in stack settings, but repository and organizational security policies must still be followed.

---

## Create and Configure the Stacks

### Development stack

Create the stack:

```bash
pulumi stack init dev
```

Configure it:

```bash
pulumi config set namespaceName pulumi-dev --stack dev
pulumi config set replicas 1 --stack dev
pulumi config set image nginx:1.27-alpine --stack dev
pulumi config set environmentMessage "Development environment managed by Pulumi" --stack dev
pulumi config set localTestPort 8081 --stack dev
pulumi config set podQuota "10" --stack dev
pulumi config set cpuRequest 50m --stack dev
pulumi config set memoryRequest 64Mi --stack dev
pulumi config set cpuLimit 250m --stack dev
pulumi config set memoryLimit 128Mi --stack dev
```

Review the configuration:

```bash
pulumi config --stack dev
cat Pulumi.dev.yaml
```

`pulumi stack init` creates an empty stack in the active backend. It does not create Kubernetes resources. `pulumi config set` writes stack settings; the desired resource graph is evaluated only when `pulumi preview` or `pulumi up` runs.

### Staging stack

Create the stack:

```bash
pulumi stack init staging
```

Configure it:

```bash
pulumi config set namespaceName pulumi-staging --stack staging
pulumi config set replicas 2 --stack staging
pulumi config set image nginx:1.27-alpine --stack staging
pulumi config set environmentMessage "Staging environment managed by Pulumi" --stack staging
pulumi config set localTestPort 8082 --stack staging
pulumi config set podQuota "20" --stack staging
pulumi config set cpuRequest 100m --stack staging
pulumi config set memoryRequest 128Mi --stack staging
pulumi config set cpuLimit 500m --stack staging
pulumi config set memoryLimit 256Mi --stack staging
```

Review the stacks and staging configuration:

```bash
pulumi stack ls
pulumi config --stack staging
cat Pulumi.staging.yaml
```

The two stack settings files do not represent two copies of the application program. `Pulumi.yaml` remains the single shared program.

---

## Preview and Deploy Development

Before creating resources, verify the active Kubernetes context again:

```bash
kubectl config current-context
kubectl config view --minify
```

Preview the `dev` stack:

```bash
pulumi preview --stack dev --diff
```

During preview:

```text
Pulumi.yaml + Pulumi.dev.yaml
        ↓
YAML Runtime resolves config and ${pulumi.stack}
        ↓
Pulumi Engine builds the resource graph
        ↓
Engine reads dev state from the backend
        ↓
Kubernetes Provider performs Check and Diff
        ↓
Preview prints the planned create operations
```

Preview does not create Kubernetes resources.

Deploy development:

```bash
pulumi up --stack dev
```

After confirmation, the Engine executes operations according to the dependency graph:

1. The Kubernetes provider is configured.
2. The `pulumi-dev` Namespace is created.
3. The ResourceQuota and ConfigMap become creatable.
4. The Deployment is created after its required dependencies are available.
5. The Service is created.
6. Kubernetes controllers create the ReplicaSet and Pod.
7. Pulumi records the completed checkpoint in the `dev` stack state.

The Deployment flow inside Kubernetes is:

```text
Pulumi Kubernetes Provider sends Deployment object
        ↓
API Server authenticates and admits the object
        ↓
Deployment Controller creates a ReplicaSet
        ↓
ReplicaSet Controller creates a Pod
        ↓
Scheduler selects a Node
        ↓
Kubelet starts the Nginx container
        ↓
Readiness probe succeeds
        ↓
Service EndpointSlice includes the Pod
```

---

## Validate Development

Display stack outputs:

```bash
pulumi stack output --stack dev
```

Validate the Namespace and resources:

```bash
kubectl get namespace pulumi-dev
kubectl -n pulumi-dev get resourcequota
kubectl -n pulumi-dev get configmap
kubectl -n pulumi-dev get deployment,replicaset,pod,service
kubectl -n pulumi-dev rollout status deployment/multi-stack-web
kubectl -n pulumi-dev get endpointslice \
  -l kubernetes.io/service-name=multi-stack-web
```

Expected initial state:

- Namespace `pulumi-dev` exists.
- Deployment reports `1/1` Ready.
- One Pod is Running and Ready.
- The EndpointSlice contains a Pod address.
- The Service exists on port `80`.

A Pod may be `Running` but not yet `Ready`. A not-ready Pod should not be included as a normal Service endpoint.

Diagnostic commands:

```bash
kubectl -n pulumi-dev describe deployment multi-stack-web
kubectl -n pulumi-dev describe pod \
  -l app.kubernetes.io/name=multi-stack-web
kubectl -n pulumi-dev logs deployment/multi-stack-web
```

### HTTP test from the local machine

In terminal 1:

```bash
kubectl -n pulumi-dev port-forward service/multi-stack-web 8081:80
```

In terminal 2:

```bash
curl -s http://127.0.0.1:8081
```

The HTML response should include:

```text
Stack: dev
Namespace: pulumi-dev
Message: Development environment managed by Pulumi
```

The port-forward process is temporary. It is not a Kubernetes resource and is not stored in Pulumi state.

### In-cluster DNS test

Run a temporary curl Pod:

```bash
kubectl -n pulumi-dev run curl-test \
  --rm -it \
  --restart=Never \
  --image=curlimages/curl \
  -- http://multi-stack-web
```

This Pod is created outside Pulumi and is not present in Pulumi state. The `--rm` option deletes it after completion.

---

## Preview and Deploy Staging

Preview and deploy the same program with staging configuration:

```bash
pulumi preview --stack staging --diff
pulumi up --stack staging
```

The same `Pulumi.yaml` is evaluated again, but the configuration and state belong to `staging`.

The staging Engine run does not see the `dev` resources as resources in the staging state and must not update or delete them.

---

## Validate Staging

Display outputs and resources:

```bash
pulumi stack output --stack staging
kubectl get namespace pulumi-staging
kubectl -n pulumi-staging get deployment,pod,service,resourcequota
kubectl -n pulumi-staging rollout status deployment/multi-stack-web
```

In terminal 1:

```bash
kubectl -n pulumi-staging port-forward service/multi-stack-web 8082:80
```

In terminal 2:

```bash
curl -s http://127.0.0.1:8082
```

The response should include:

```text
Stack: staging
Namespace: pulumi-staging
Message: Staging environment managed by Pulumi
```

The initial staging Deployment should have two replicas and larger CPU and memory settings than development.

---

## Prove Stack Independence

List both Pulumi stacks and compare the two environments:

```bash
pulumi stack ls

kubectl get namespace pulumi-dev pulumi-staging
kubectl -n pulumi-dev get deployment multi-stack-web
kubectl -n pulumi-staging get deployment multi-stack-web

kubectl -n pulumi-dev get pods \
  -l app.kubernetes.io/name=multi-stack-web
kubectl -n pulumi-staging get pods \
  -l app.kubernetes.io/name=multi-stack-web
```

The logical resource name is the same in both stacks, for example `webDeployment`. The Pulumi URNs differ because each URN includes the stack name. The physical Kubernetes IDs also differ because they include different namespaces.

```text
URN in dev:
...::dev::kubernetes:apps/v1:Deployment::webDeployment

Physical ID:
pulumi-dev/multi-stack-web

URN in staging:
...::staging::kubernetes:apps/v1:Deployment::webDeployment

Physical ID:
pulumi-staging/multi-stack-web
```

---

## Inspect Stack State

Export each stack for controlled inspection:

```bash
pulumi stack export --stack dev --file dev-state.json
pulumi stack export --stack staging --file staging-state.json
```

Inspect resource identity fields:

```bash
jq '.deployment.resources[] | {urn, type, id}' dev-state.json
jq '.deployment.resources[] | {urn, type, id}' staging-state.json
```

> Exported state may contain sensitive outputs or metadata. Do not commit exported state to Git. Use export for controlled backup, migration, and troubleshooting, not as a normal state-editing workflow.

Delete the temporary exports after the exercise:

```bash
rm -f dev-state.json staging-state.json
```

---

## Update Only Development

Change the development replica count and environment message:

```bash
pulumi config set replicas 3 --stack dev
pulumi config set environmentMessage \
  "Development environment - version 2" \
  --stack dev
```

Preview and apply only `dev`:

```bash
pulumi preview --stack dev --diff
pulumi up --stack dev
```

Expected behavior:

- `spec.replicas` changes from `1` to `3`.
- The ConfigMap content changes.
- The `staging` stack does not change.
- Updating only ConfigMap data does not necessarily cause a Deployment rollout because the pod template is unchanged.
- Kubernetes eventually updates projected ConfigMap volume files.
- Nginx reads the updated file on subsequent requests.

Confirm independence:

```bash
kubectl -n pulumi-dev get deployment multi-stack-web
kubectl -n pulumi-staging get deployment multi-stack-web

curl -s http://127.0.0.1:8081
curl -s http://127.0.0.1:8082
```

Expected result:

- Development has three replicas and the version 2 message.
- Staging remains at two replicas with its original message.

---

## Trigger a Rolling Update in Staging

Changing a resource limit changes the Deployment pod template and triggers a new ReplicaSet.

Update the staging memory limit:

```bash
pulumi config set memoryLimit 384Mi --stack staging
pulumi preview --stack staging --diff
pulumi up --stack staging
```

Observe the rollout:

```bash
kubectl -n pulumi-staging rollout status deployment/multi-stack-web
kubectl -n pulumi-staging get replicaset
kubectl -n pulumi-staging get pods -w
```

Expected behavior:

1. Preview displays the memory limit change.
2. The Deployment controller creates a new ReplicaSet.
3. New Pods are started with the updated pod template.
4. With `maxUnavailable: 0`, existing Ready Pods remain until replacements are Ready.
5. Old Pods are terminated after the new Pods become Ready.

Pulumi manages the Deployment object, not the child Pods directly.

---

## Drift Detection and Recovery

Drift occurs when the actual provider state differs from the current Pulumi state and declared program.

### Create controlled drift

Scale the development Deployment manually:

```bash
kubectl -n pulumi-dev scale deployment/multi-stack-web --replicas=5
kubectl -n pulumi-dev get deployment multi-stack-web
```

Pulumi configuration still declares three replicas, but Kubernetes now has five.

### Detect drift without modifying state

```bash
pulumi refresh --preview-only --stack dev
```

`refresh --preview-only` queries the provider and displays differences without changing the Pulumi state or the Kubernetes cluster.

### Remediation: restore the cluster to the declared configuration

Use the Pulumi program as the source of truth:

```bash
pulumi preview --refresh --stack dev --diff
pulumi up --refresh --stack dev
```

The `--refresh` option first reads the actual provider state. The subsequent update reapplies the configured replica count of three.

### Adoption: accept a valid manual change

If five replicas are the new approved value, update both Pulumi state and stack configuration:

```bash
pulumi refresh --stack dev
pulumi config set replicas 5 --stack dev
pulumi preview --stack dev
```

The final preview should report no changes.

> Running only `pulumi refresh` is not enough to adopt a desired manual configuration permanently. If the program still declares a different value, the next `pulumi up` may restore the program value.

---

## Why Deleting a Pod Is Usually Not Persistent Pulumi Drift

Delete one staging Pod:

```bash
POD_NAME=$(kubectl -n pulumi-staging get pod \
  -l app.kubernetes.io/name=multi-stack-web \
  -o jsonpath='{.items[0].metadata.name}')

kubectl -n pulumi-staging delete pod "$POD_NAME"
kubectl -n pulumi-staging get pods -w
```

The Deployment controller immediately creates a replacement Pod because the Deployment still declares two replicas.

Pulumi manages the Deployment. The Pod is a child resource reconciled by Kubernetes. Once Kubernetes restores the Deployment's desired replica state, Pulumi may see no persistent drift in the managed Deployment resource.

```text
Pulumi reconciliation:
Pulumi Program → Deployment object

Kubernetes reconciliation:
Deployment → ReplicaSet → Pods
```

Understanding these two reconciliation loops is essential during troubleshooting.

---

## Provider and Namespace Behavior

### Why each stack gets its own provider resource

`k8sProvider` exists independently inside each stack state.

```text
dev provider     → default namespace pulumi-dev
staging provider → default namespace pulumi-staging
```

The logical provider name is the same, but the URN is different because the stack name is different.

### Benefits of an explicit provider

- The intended namespace is visible and reviewable in the program.
- Provider version can be pinned.
- Resources explicitly identify which provider they use.
- Advanced projects can use multiple providers for multiple clusters or namespaces.
- The configuration is less dependent on an accidentally changed default namespace.

The cluster is still selected through kubeconfig in this project. For a real multi-cluster design, configure the provider's kubeconfig or context explicitly as well.

### Why `metadata.namespace` is omitted

This project uses the provider default namespace to demonstrate provider-scoped configuration.

Some production teams prefer explicit `metadata.namespace` on every namespaced resource. Others prefer one namespace-scoped provider to reduce repetition. Select one policy, document it, and enforce it consistently.

---

## Dependency Graph

Pulumi builds a dependency graph for ordering and parallel execution.

| Relationship | Dependency type | Reason |
|---|---|---|
| Deployment → ConfigMap | Implicit | The Deployment uses `${webContent.metadata.name}`. |
| ResourceQuota → Namespace | Explicit | No direct Namespace output is used in its properties. |
| Service → Deployment | No hard dependency required | A Service can exist before matching Pods become Ready. |
| Provider → kubeconfig | Provider configuration | The provider reads context and credentials during configuration. |

Do not add `dependsOn` to every resource. Unnecessary dependencies reduce parallelism and make the graph harder to reason about. Add explicit dependencies only when a real ordering requirement cannot be inferred from resource inputs and outputs.

---

## What Namespace Isolation Does and Does Not Provide

| Requirement | Is Namespace alone sufficient? | Additional control |
|---|---|---|
| Reuse names for namespaced resources | Yes | Namespace scope |
| Limit Pod count | No | ResourceQuota |
| Default requests and limits | No | LimitRange |
| Separate user permissions | No | RBAC |
| Block traffic between environments | No | NetworkPolicy |
| Separate nodes or runtimes | No | NodeSelector, taints, RuntimeClass |
| Full failure-domain separation | No | Separate clusters or multi-cluster architecture |

This project implements a Pod-count ResourceQuota. Future extensions may add LimitRange, RoleBinding, and NetworkPolicy resources driven by the same stack configuration.

---

## Optional Resource Protection

Pulumi's `protect` resource option prevents accidental deletion.

Example for the Namespace:

```yaml
appNamespace:
  type: kubernetes:core/v1:Namespace
  properties:
    metadata:
      name: ${namespaceName}
      labels: ${appLabels}
  options:
    provider: ${k8sProvider}
    protect: true
```

After adding `protect`, run an update so the option is recorded in state:

```bash
pulumi up --stack dev
```

A later destroy will stop when it reaches the protected resource.

To remove it safely:

1. Change `protect` to `false` or remove the option.
2. Run `pulumi up` so state records the change.
3. Run `pulumi destroy`.

Do not delete stack state merely to bypass protection.

---

## Troubleshooting

### Pulumi is targeting the wrong cluster

```bash
kubectl config current-context
kubectl config view --minify
pulumi preview --stack dev --diff
```

The explicit provider selects the namespace, but the cluster still comes from kubeconfig. Always verify the context before `pulumi up`.

### Namespace already exists

If a Namespace already exists and is managed elsewhere, Pulumi may receive an `AlreadyExists` error.

Choose one ownership model:

- import the existing Namespace into the stack;
- remove Namespace management from this stack;
- manage shared namespaces in a separate platform stack.

Do not delete an existing Namespace without understanding its current owner and workloads.

### Pod is in `ImagePullBackOff`

```bash
kubectl -n pulumi-dev describe pod \
  -l app.kubernetes.io/name=multi-stack-web
kubectl -n pulumi-dev get events --sort-by=.lastTimestamp
```

Check:

- image name and tag;
- registry authentication;
- cluster DNS and internet access;
- registry rate limits;
- image architecture compatibility.

Pulumi may successfully create the Deployment object while the workload fails to become Ready.

### Service does not return a response

```bash
kubectl -n pulumi-dev get pod --show-labels
kubectl -n pulumi-dev describe service multi-stack-web
kubectl -n pulumi-dev get endpointslice \
  -l kubernetes.io/service-name=multi-stack-web
```

Compare the Service selector with Pod labels. Confirm readiness probes are passing. A Running but NotReady Pod does not normally receive Service traffic.

### ResourceQuota prevents Pod creation

```bash
kubectl -n pulumi-dev describe resourcequota application-quota
kubectl -n pulumi-dev get events --sort-by=.lastTimestamp
```

If replicas exceed the configured Pod quota, the ReplicaSet cannot create all requested Pods.

### ConfigMap changed but the page did not update immediately

Projected ConfigMap volumes are eventually consistent and may take time to update.

Additional considerations:

- A `subPath` mount does not receive automatic ConfigMap file updates.
- Some applications cache files.
- Some applications read configuration only at startup.
- Such applications may require a controlled rollout after ConfigMap changes.

### Namespace is stuck in `Terminating`

```bash
kubectl get namespace pulumi-dev -o yaml
kubectl api-resources --verbs=list --namespaced -o name | \
  xargs -n 1 kubectl get -n pulumi-dev --ignore-not-found
```

Inspect remaining namespaced resources and finalizers. Do not remove finalizers blindly; doing so may skip required external cleanup.

### Provider plugin problems

Check provider installation and preview output:

```bash
pulumi plugin ls
pulumi preview --stack dev --diff
```

If required, install the pinned provider version:

```bash
pulumi plugin install resource kubernetes 4.32.0
```

### Missing required stack configuration

List stack configuration:

```bash
pulumi config --stack dev
```

Set missing values using the commands in [Create and Configure the Stacks](#create-and-configure-the-stacks).

### Wrong stack selected

Prefer explicit `--stack` in scripts and CI/CD:

```bash
pulumi preview --stack dev
pulumi up --stack dev
```

This reduces the risk of updating the wrong environment.

---

## Cleanup

Destroy development first and verify staging remains:

```bash
pulumi preview --stack dev --destroy
pulumi destroy --stack dev

kubectl get namespace pulumi-dev pulumi-staging
kubectl -n pulumi-staging get deployment,pod,service
```

The staging stack and namespace should remain healthy.

Remove the empty development stack:

```bash
pulumi stack rm dev
```

Destroy staging:

```bash
pulumi preview --stack staging --destroy
pulumi destroy --stack staging
```

Remove the empty staging stack:

```bash
pulumi stack rm staging
```

Safe cleanup order:

```text
pulumi destroy
        ↓
Verify provider resources were removed
        ↓
pulumi stack rm
```

Do not remove stack state while real resources are still expected to be managed by that stack.

---

## Production Considerations

This project is designed as a teaching lab. For production environments, consider the following:

- Use immutable image tags or image digests instead of mutable tags such as `latest`.
- Upgrade the Kubernetes provider through a controlled process and preview every stack.
- Use a shared, backed-up backend with appropriate locking and access control.
- Keep critical state outside the failure domain of the resources it manages.
- Add RBAC, NetworkPolicy, LimitRange, PodDisruptionBudget, Ingress or Gateway API, TLS, monitoring, alerting, and audit controls.
- Store non-sensitive stack configuration in Git.
- Store credentials and tokens as Pulumi secrets or in an external secret manager.
- Explicitly specify `--stack` in automation.
- Use `pulumi preview --refresh` and human review before sensitive changes.
- Do not assume namespaces provide full security or failure isolation.
- Sensitive production environments may require separate clusters, accounts, subscriptions, or projects.
- Use an external high-availability backend if the Kubernetes cluster itself is a critical managed target.

---

## Exercises

1. Create a `qa` stack in namespace `pulumi-qa` with two replicas.
2. Add a `servicePort` stack configuration value and make the Service port configurable.
3. Add a `LimitRange` to define default requests and limits in each namespace.
4. Add a `NetworkPolicy` that accepts ingress only from Pods with an approved label.
5. Change the staging Service from `ClusterIP` to `NodePort`, inspect the preview, and explain the security impact before applying it.
6. Import a pre-existing Namespace with `pulumi import` and document the difference between import and create.
7. Change the Service manually, detect drift with `refresh --preview-only`, and decide between remediation and adoption.
8. Read service outputs from another Pulumi project with a StackReference.
9. Configure a second Kubernetes provider that targets another cluster or context.
10. Add a protected production Namespace and document the safe unprotect-and-destroy procedure.

---

## Final Verification Checklist

- [ ] Pulumi is connected to the intended backend.
- [ ] `kubectl` is connected to the intended Kubernetes context.
- [ ] Required RBAC permissions return `yes`.
- [ ] Both `dev` and `staging` stacks exist.
- [ ] `Pulumi.dev.yaml` and `Pulumi.staging.yaml` have different settings.
- [ ] `pulumi-dev` and `pulumi-staging` namespaces exist.
- [ ] Development initially has one replica.
- [ ] Staging initially has two replicas.
- [ ] Each HTTP page displays the correct stack, namespace, and message.
- [ ] Updating `dev` does not change `staging`.
- [ ] Updating the staging pod template creates a RollingUpdate.
- [ ] Drift is detected with `pulumi refresh --preview-only`.
- [ ] Remediation restores the declared configuration.
- [ ] Adoption updates both state and configuration.
- [ ] Deleting a Pod is not confused with persistent Deployment drift.
- [ ] Destroying one stack does not delete the other environment.
- [ ] Exported state files are not committed to Git.

---

## Mental Model

```text
One Project = one shared infrastructure program
        ↓
Each Stack = independent config + independent state
        ↓
Stack Config selects namespace, replicas, and policies
        ↓
Explicit Provider selects Kubernetes behavior and default namespace
        ↓
Pulumi Engine computes the graph and calls the Kubernetes Provider
        ↓
Kubernetes API stores the declared objects
        ↓
Kubernetes controllers create and reconcile child resources
        ↓
Updates, drift checks, and destroy operations happen per stack
```

Multi-environment does not require multiple copies of the program. The shared program defines common intent, while stack configuration introduces controlled differences. Pulumi stacks provide independent infrastructure lifecycles, and Kubernetes namespaces provide namespaced resource scope.

---

## Official References

- Pulumi YAML Language Reference: https://www.pulumi.com/docs/iac/languages-sdks/yaml/yaml-language-reference/
- Pulumi Stacks: https://www.pulumi.com/docs/iac/concepts/stacks/
- Pulumi Configuration: https://www.pulumi.com/docs/iac/concepts/config/
- Stack Settings File Reference: https://www.pulumi.com/docs/iac/concepts/projects/stack-settings-file/
- Pulumi Kubernetes Provider: https://www.pulumi.com/registry/packages/kubernetes/
- Pulumi Kubernetes Installation and Configuration: https://www.pulumi.com/registry/packages/kubernetes/installation-configuration/
- Kubernetes Namespaces: https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/
- Kubernetes Deployments: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- Kubernetes ResourceQuota: https://kubernetes.io/docs/concepts/policy/resource-quotas/
- Kubernetes Probes: https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/
