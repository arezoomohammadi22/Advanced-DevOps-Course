# Pulumi Projects, Stacks, Configuration, Secrets, and Outputs

This guide explains how one Pulumi program can manage multiple isolated environments without copying the infrastructure source code. It develops the relationship between projects, stacks, configuration, secrets, outputs, state boundaries, and environment lifecycle through a complete TypeScript and Docker lab.

The practical result is one shared `index.ts` program that creates two independent Nginx environments named `dev` and `staging`. Each stack has its own state, port, container name, debug setting, configuration, encrypted token, outputs, and lifecycle, while both stacks use the same project and resource logic.

---

## Learning Outcomes

After completing this guide, you should be able to:

- Explain why copying infrastructure code for every environment creates long-term maintenance and security problems.
- Define the boundary and purpose of a Pulumi project.
- Explain why a stack is more than an environment variable.
- Distinguish project name, logical resource name, physical resource name, and Pulumi URN.
- Create, select, inspect, destroy, and remove stacks.
- Use stack configuration to separate environment-specific data from infrastructure logic.
- Choose between optional getters, required getters, typed getters, and structured configuration.
- Store sensitive values with `--secret` and read them with `requireSecret`.
- Explain secret encryption and secret propagation.
- Design stack outputs as a stable interface rather than temporary log output.
- Use `pulumi.interpolate`, `apply`, and `pulumi.all` correctly.
- Create and compare development and staging environments from one source program.
- Rotate a secret, test missing required configuration, and change stack settings safely.
- Distinguish Pulumi configuration secrets from a dedicated runtime secret manager.
- Apply project, stack, configuration, state, and version-control best practices.
- Troubleshoot missing configuration, port conflicts, plaintext secrets, unresolved outputs, and wrong-stack deployments.

---

## Why One Program Should Manage Multiple Environments

A common early approach is to create separate copies of infrastructure code for development, staging, and production. This appears simple, but the copies quickly diverge:

- A security fix is applied to one environment but not another.
- A provider upgrade reaches development but not staging.
- Naming, tags, policies, and resource options become inconsistent.
- Reviewers cannot easily determine which differences are intentional.
- A bug fix must be repeated across multiple codebases.
- Production can remain on an obsolete architecture because the copies no longer evolve together.

Pulumi solves this problem through several connected concepts:

- **Project** — the program and logical boundary
- **Stack** — one isolated deployed instance of the program
- **Configuration** — stack-specific input values
- **Secret** — sensitive stack input protected by Pulumi's secret model
- **Output** — a value exposed by the deployment for humans or automation

The shared resource logic remains in source code. Environment differences are represented as explicit configuration rather than code duplication.

### Scenario

Development requires:

- Host port `8080`
- Debug enabled
- A development token

Staging requires:

- Host port `8081`
- Debug disabled
- A separate staging token

The tokens must not be stored as plaintext in Git. Both environments should use the same Nginx deployment logic.

A correct design treats values such as region, port, replica count, instance size, domain, image tag, retention period, and feature flags as configuration candidates. Passwords, tokens, private keys, and similar sensitive values must be secrets. Resource-construction logic should remain in code.

---

## Project: The Program Boundary

A directory containing `Pulumi.yaml` is recognized as a Pulumi project. The CLI searches from the current directory toward parent directories and uses the nearest project file.

The project defines:

- Project name
- Runtime
- Description
- Optional program entry location
- The logical scope to which stacks belong
- The default namespace for project configuration keys
- Part of every resource URN

A project is not a deployment. It is the reusable program definition. Real resources appear only when the project is evaluated for a specific stack.

### Example `Pulumi.yaml`

```yaml
name: pulumi-multi-env
runtime: nodejs
description: Multi-environment Pulumi project for Project, Stack, Config and Secret training
```

The filename begins with a capital `P`. With `runtime: nodejs`, Pulumi starts the Node.js language host. A `main` property can point to a subdirectory, but the lab keeps a simple root-level `index.ts`.

---

## Project Name, Logical Name, Physical Name, and URN

These identities are different and should not be confused.

### Project name

`pulumi-multi-env` identifies the project boundary.

### Logical resource name

The string passed to a resource constructor, for example:

```typescript
new docker.Container("nginxContainer", { /* ... */ });
```

`nginxContainer` is the logical name used in Pulumi state.

### Physical resource name

The real Docker name can be:

```text
pulumi-multi-env-dev
```

This is the name visible to Docker.

### Pulumi URN

The URN contains stack, project, type, parent information where relevant, and logical name. It is Pulumi's internal identity for lifecycle tracking.

The same logical name can safely exist in `dev` and `staging` because each stack has independent state and URNs.

Renaming a logical resource is not automatically cosmetic. Without aliases or migration planning, Pulumi can interpret it as deletion of the old resource and creation of a new one.

---

## Stack: An Isolated Instance of the Program

A stack is an independent instance of a Pulumi project. It owns separate:

- Configuration
- Secrets
- State checkpoint
- Outputs
- Update history
- Managed resources
- Lifecycle operations

A stack is not simply a variable named `environment`. A normal variable changes program behavior, but a stack is a complete management boundary. `pulumi up`, `pulumi refresh`, and `pulumi destroy` target the active stack. The backend stores a separate checkpoint for each stack.

### Stack commands

```bash
pulumi stack ls
pulumi stack
pulumi stack init dev
pulumi stack select dev
pulumi stack --show-urns
```

- `pulumi stack ls` lists project stacks and marks the active one.
- `pulumi stack` displays the active stack.
- `pulumi stack init dev` creates and selects a new stack.
- `pulumi stack select dev` switches to an existing stack.
- `pulumi stack --show-urns` includes Pulumi resource identities.

> Verify the active stack before every preview, update, refresh, or destroy. Many incidents are caused by running a valid command against the wrong environment.

### Fully qualified stack names

In Pulumi Cloud, a stack can be identified as:

```text
organization/project/stack
```

Short names such as `dev` are convenient inside a known project. Automation across several projects should prefer unambiguous stack references.

---

## Prerequisites

Verify the required tools:

```bash
pulumi version
node --version
npm --version
docker version
docker info
```

If `docker info` fails, fix Docker connectivity or permissions before using the Docker provider.

---

## Create the Multi-Environment Project

Use a local backend for the isolated lab:

```bash
pulumi login --local
mkdir pulumi-multi-env
cd pulumi-multi-env
pulumi new typescript
```

Use:

- Project: `pulumi-multi-env`
- Stack: `dev`
- Runtime: Node.js/TypeScript

Install the Docker provider:

```bash
npm install @pulumi/docker
npm list @pulumi/pulumi
npm list @pulumi/docker
```

Commit `package.json` and `package-lock.json`. Do not commit `node_modules/`.

---

## Configuration: Separate Environment Data from Resource Logic

Pulumi configuration is stack-specific. The same program receives different values when a different stack is active.

Create a configuration object:

```typescript
const config = new pulumi.Config();
```

By default, keys are scoped to the current project. A key named `hostPort` appears in the settings file as:

```text
pulumi-multi-env:hostPort
```

### Optional getters

```typescript
const imageName = config.get("imageName") ?? "nginx:alpine";
const restartPolicy = config.get("restartPolicy") ?? "unless-stopped";
const enableDebug = config.getBoolean("enableDebug") ?? false;
```

`get`, `getBoolean`, `getNumber`, and related methods return `undefined` when the key does not exist. Use them only when an absent value has a safe, intentional default.

### Required getters

```typescript
const environment = config.require("environment");
const hostPort = config.requireNumber("hostPort");
```

`require` and typed `require...` methods stop program evaluation when the key is missing. Use them when silently choosing a default could deploy to the wrong environment or create an unsafe architecture.

### Choosing between `get` and `require`

Use `require` for values such as:

- Cloud account or subscription
- Region when the default could be wrong
- Production domain
- Required instance size
- Mandatory network identifier
- External port where collision must be explicit

Use an optional getter with a default for values with a genuinely safe baseline, such as debug disabled or a minimal development replica count.

Typed getters are important because stack settings are stored in YAML but the program needs correct runtime types.

---

## Configure Development

```bash
pulumi stack select dev
pulumi config set environment development
pulumi config set --type int hostPort 8080
pulumi config set imageName nginx:alpine
pulumi config set restartPolicy unless-stopped
pulumi config set --type bool enableDebug true
pulumi config set --secret appToken dev-training-token
pulumi config
```

`--type int` and `--type bool` preserve intended types in the settings file. The token is marked as a secret before storage.

---

## Secrets and Secret Propagation

Read a required secret:

```typescript
const appToken = config.requireSecret("appToken");
```

Unlike `require`, `requireSecret` returns a secret `pulumi.Output<string>`. The value is encrypted in stack settings and redacted in ordinary CLI output.

A derived value remains secret:

```typescript
const tokenIsConfigured = appToken.apply(value => value.length > 0);
```

This behavior is called secret propagation. Pulumi tracks sensitivity metadata through output transformations so derived values do not become public accidentally.

### Example stack settings structure

The exact encrypted values vary by secrets provider:

```yaml
encryptionsalt: v1:REDACTED-FOR-DOCUMENTATION
config:
  pulumi-multi-env:environment: development
  pulumi-multi-env:hostPort: 8080
  pulumi-multi-env:imageName: nginx:alpine
  pulumi-multi-env:restartPolicy: unless-stopped
  pulumi-multi-env:enableDebug: true
  pulumi-multi-env:appToken:
    secure: v1:ENCRYPTED-CIPHERTEXT
```

Encryption protects stored representation. The plaintext still exists temporarily at runtime when the provider or resource needs it. Therefore, avoid logging secret values and restrict access to the backend, CI environment, and target platform.

---

## Complete Program

Replace `index.ts` with:

```typescript
import * as pulumi from "@pulumi/pulumi";
import * as docker from "@pulumi/docker";

const config = new pulumi.Config();

const environment = config.require("environment");
const hostPort = config.requireNumber("hostPort");
const imageName = config.get("imageName") ?? "nginx:alpine";
const restartPolicy = config.get("restartPolicy") ?? "unless-stopped";
const enableDebug = config.getBoolean("enableDebug") ?? false;
const appToken = config.requireSecret("appToken");

const project = pulumi.getProject();
const stack = pulumi.getStack();
const physicalContainerName = `${project}-${stack}`;

const image = new docker.RemoteImage("nginxImage", {
    name: imageName,
    keepLocally: true,
});

const container = new docker.Container("nginxContainer", {
    name: physicalContainerName,
    image: image.imageId,
    restart: restartPolicy,
    ports: [{
        internal: 80,
        external: hostPort,
        protocol: "tcp",
    }],
    envs: [
        `APP_ENV=${environment}`,
        `DEBUG=${enableDebug}`,
        appToken.apply(value => `APP_TOKEN=${value}`),
    ],
    labels: [
        { label: "managed-by", value: "pulumi" },
        { label: "environment", value: environment },
        { label: "pulumi-project", value: project },
        { label: "pulumi-stack", value: stack },
    ],
});

export const projectName = project;
export const stackName = stack;
export const containerName = container.name;
export const containerId = container.id;
export const applicationUrl = pulumi.interpolate`http://localhost:${hostPort}`;
export const tokenIsConfigured = appToken.apply(value => value.length > 0);
```

---

## Program Analysis

### Project and stack identity

```typescript
const project = pulumi.getProject();
const stack = pulumi.getStack();
const physicalContainerName = `${project}-${stack}`;
```

This produces predictable physical names:

- `pulumi-multi-env-dev`
- `pulumi-multi-env-staging`

The logical resource names remain the same in both stacks because state is isolated.

### Image dependency

```typescript
image: image.imageId,
```

`image.imageId` is a resource output. It creates an implicit dependency from the container to the image resource.

### Environment values

Ordinary strings are passed directly. The token requires `apply` because it is a secret output:

```typescript
appToken.apply(value => `APP_TOKEN=${value}`)
```

Using an environment variable makes secret propagation visible in the lab. It is not automatically the best production secret-delivery pattern. Runtime retrieval from a dedicated secret manager can reduce exposure.

### Labels

Labels make ownership and environment visible from Docker. Similar metadata should be applied consistently in cloud and Kubernetes environments for operations, cost, audit, and cleanup.

### Outputs

The project and stack names are ordinary synchronous strings. The container name and ID are resource outputs. `applicationUrl` uses Pulumi interpolation. `tokenIsConfigured` remains secret because it was derived from a secret.

---

## Preview and Deploy Development

```bash
pulumi stack
pulumi config
pulumi preview --diff
pulumi up --diff
```

Review:

- Active stack
- Required configuration
- Physical container name
- Image
- Port
- Environment variables
- Labels
- Creates, replacements, and deletes

Validate the resource:

```bash
docker ps --filter name=pulumi-multi-env-dev
docker inspect pulumi-multi-env-dev
curl http://localhost:8080
pulumi stack output
pulumi stack output applicationUrl
```

Inspecting the container can reveal environment variables, including the runtime token. This demonstrates that encryption in Pulumi state does not prevent the target platform from receiving plaintext when the resource requires it.

### Secret output behavior

```bash
pulumi stack output tokenIsConfigured
pulumi stack output tokenIsConfigured --show-secrets
```

Ordinary output hides the value. `--show-secrets` deliberately reveals it and should be used only in a controlled context.

---

## Create Staging

```bash
pulumi stack init staging
pulumi config set environment staging
pulumi config set --type int hostPort 8081
pulumi config set imageName nginx:alpine
pulumi config set restartPolicy unless-stopped
pulumi config set --type bool enableDebug false
pulumi config set --secret appToken staging-training-token
pulumi config
pulumi preview --diff
pulumi up --diff
```

Compare both environments:

```bash
docker ps --filter label=managed-by=pulumi
curl http://localhost:8080
curl http://localhost:8081
pulumi stack ls
pulumi stack output applicationUrl --stack dev
pulumi stack output applicationUrl --stack staging
```

The two stacks use one program but maintain separate configuration and state.

---

## Stack Settings Files and Version Control

A useful `.gitignore` can contain:

```gitignore
node_modules/
.pulumi/
*.log
.env
.env.*
# Pulumi.<stack>.yaml files are intentionally kept in Git.
```

Stack settings files are commonly committed because they document environment configuration and store secrets as ciphertext. However:

- Never store sensitive values without `--secret`.
- Encryption does not make repository access irrelevant.
- Protect the secrets provider and backend.
- Review configuration changes through pull requests.
- Do not commit local backend state or raw state exports.
- Follow organizational policy if stack settings must be stored elsewhere.

If plaintext was committed before conversion to a secret, encrypting the current value does not erase Git history. Rotate the credential and clean history through the approved incident process.

---

## Outputs as the Stack Interface

A stack output is the supported interface through which other tools or stacks consume deployment results. Good outputs are small, stable, and intentional.

Useful outputs include:

- Application endpoint
- Load-balancer hostname
- Database host
- Resource group or namespace name
- Service identity
- Queue or topic name

Avoid exporting:

- Entire large provider objects
- Sensitive values unnecessarily
- Unstable internal details
- Values that encourage tight coupling

### Resource output versus stack output

A resource output is a `pulumi.Output<T>` produced by a resource. It becomes a stack output only when exported from the program.

### `apply`

Use `apply` when a derived value depends on an output:

```typescript
const tokenIsConfigured = appToken.apply(value => value.length > 0);
```

The callback executes when the value is available. Do not use `apply` as a general escape hatch for uncontrolled side effects.

### `pulumi.interpolate`

Use interpolation for strings containing outputs:

```typescript
export const applicationUrl = pulumi.interpolate`http://localhost:${hostPort}`;
```

### `pulumi.all`

Combine several outputs:

```typescript
const endpoint = pulumi
    .all([container.name, image.imageId])
    .apply(([name, imageId]) => `${name} uses ${imageId}`);

export const deploymentSummary = endpoint;
```

Outputs carry value timing, dependency information, and secret metadata. Treating them as ordinary strings can produce `[object Object]`, unknown values during preview, or lost dependency relationships.

---

## Structured Configuration

Flat keys are convenient for small projects. Related settings can be grouped into structured objects.

Create a nested configuration:

```bash
pulumi config set --path service.hostPort 8082
pulumi config set --path service.enableDebug true
pulumi config set --path service.labels.owner platform-team
pulumi config set --path service.labels.costCenter training
```

Read it with a TypeScript interface:

```typescript
interface ServiceConfig {
    hostPort: number;
    enableDebug: boolean;
    labels: Record<string, string>;
}

const service = config.requireObject<ServiceConfig>("service");

const owner = service.labels.owner;
const port = service.hostPort;
```

TypeScript interfaces help document expected structure but do not automatically perform complete runtime schema validation. For critical configuration, add explicit validation or a schema library.

### Secret values inside structured configuration

```bash
pulumi config set --path endpoints[0].url https://example.invalid
pulumi config set --path --secret endpoints[0].token training-token
```

Be deliberate about which paths are secret and how the resulting object is read and propagated.

---

## Change Configuration and Observe the Update

Select development and change its port:

```bash
pulumi stack select dev
pulumi config set --type int hostPort 8082
pulumi preview --diff
pulumi up --diff
curl http://localhost:8082
```

The same source program now produces a different resource property for only the selected stack. Changing container port mappings can cause resource replacement. Review operational impact before applying.

---

## Test Missing Required Configuration

Remove a required key:

```bash
pulumi config rm environment
pulumi preview
```

The program should stop with a missing required configuration error before creating resources.

Restore it:

```bash
pulumi config set environment development
```

Required configuration is an executable contract. It prevents a missing critical value from silently becoming an unsafe default.

---

## Rotate a Secret

Rotate the staging token:

```bash
pulumi stack select staging
pulumi config set --secret appToken staging-training-token-v2
pulumi preview --diff
pulumi up --diff
```

Pulumi writes new ciphertext and displays the diff as secret. The target provider determines whether the change is an update or replacement.

Real secret rotation also requires:

- Producer and consumer coordination
- Credential validity windows
- Rollback plan
- Dual-key overlap where necessary
- Audit
- Revocation of the old credential
- Verification that caches and replicas received the new value

Pulumi participates in rotation but does not define the complete security lifecycle.

---

## Pulumi Config Secret Versus a Secret Manager

Pulumi configuration secrets are appropriate for sensitive stack inputs and for securely passing them to resources. Larger systems often use a dedicated platform such as:

- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager
- Pulumi ESC or another environment/secrets integration

A dedicated secret manager can provide dynamic credentials, runtime retrieval, rotation, audit, leases, and fine-grained access boundaries.

Prefer keeping a secret inside its secure system when the application can retrieve it at runtime. Injecting plaintext into a container environment makes the value visible to the container platform and to sufficiently privileged operators.

---

## Stack Lifecycle

A stack lifecycle includes:

- Initialize
- Select
- Configure
- Preview
- Update
- Inspect outputs and state
- Refresh
- Destroy managed resources
- Remove stack metadata

Destroy staging:

```bash
pulumi stack select staging
pulumi destroy --diff
pulumi stack rm staging
```

Destroy development:

```bash
pulumi stack select dev
pulumi destroy --diff
pulumi stack rm dev
```

`pulumi stack rm` removes stack metadata. Use it only after resources are destroyed or after an explicit decision to orphan or detach them. Removing state without understanding the live resources can leave unmanaged infrastructure behind.

Production stacks should use appropriate protection, approvals, backups, change windows, and secure shared backends.

---

## Troubleshooting

### Missing required configuration variable

```bash
pulumi stack
pulumi config
pulumi config get environment
pulumi config get hostPort
```

Common causes:

- The wrong stack is active.
- The key was never set for the active stack.
- The project name changed, so configuration namespace changed.
- The key spelling or type is wrong.

### Port already allocated

```bash
docker ps --format "table {{.Names}}\t{{.Ports}}"
pulumi config set --type int hostPort 8083
pulumi up
```

Development and staging cannot use the same external port on one Docker host.

### Secret stored as plaintext

Set the key again as a secret:

```bash
pulumi config set --secret appToken replacement-training-token
pulumi config
```

Then inspect Git history. If plaintext was committed or logged, rotate the real credential. Encrypting the current value does not remove historical disclosure.

### Output appears as `[object Object]` or unknown

Use `pulumi.interpolate`, `apply`, or `pulumi.all`. Do not concatenate `Output` objects as ordinary strings. Values may be unknown during preview because the provider has not created the resource yet.

### Update ran against the wrong stack

If the update has not started, cancel it and select the correct stack. If it completed, inspect the resources and state before deciding whether to revert or destroy. Immediate destruction can remove data or dependent resources.

Automation should require an explicit stack parameter and environment protection.

---

## Best Practices

- Use predictable conventions for project, stack, logical, and physical names.
- Verify active stack, backend, provider account, region, subscription, or Kubernetes context before deployment.
- Use required getters for critical values.
- Use safe defaults only for genuinely optional settings.
- Keep shared resource logic in code and environment differences in configuration.
- Commit reviewed stack settings when policy permits, but never commit plaintext credentials or local state.
- Treat outputs as a small public interface.
- Do not export sensitive or oversized internal objects.
- Use a secure shared backend with locking, backup, audit, and access control for production.
- Do not assume a stack name alone provides strong isolation. Use separate accounts, subscriptions, projects, namespaces, credentials, and policies according to risk.
- Control provider and dependency upgrades.
- Test configuration validation and resource policy.
- Plan secret rotation and recovery before production use.

---

## Exercises

1. Create a `qa` stack with port `8084`, debug disabled, environment value `quality-assurance`, and a unique secret.
2. Add a required `pageTitle` configuration value and set a different title in every stack.
3. Export `deploymentIdentity` using project and stack names through `pulumi.interpolate`.
4. Replace flat service keys with a structured `service` object containing `hostPort`, `enableDebug`, and labels.
5. Rotate a test token and explain why `tokenIsConfigured` remains secret.
6. Add a third stack and compare all stack outputs without switching stacks.
7. Rename a logical resource in a temporary branch and inspect the preview. Investigate aliases before applying it.
8. Replace environment-variable secret delivery with a dedicated secret-manager design.
9. Add validation that rejects ports outside an approved range.
10. Add CI checks that verify the active stack and inspect preview JSON before approval.

---

## Review Questions

1. Why is a project not a deployment?
2. Why is a stack more than an environment variable?
3. How can the same logical resource name exist in two stacks safely?
4. When should `requireNumber` be used instead of `getNumber`?
5. Why does a value derived from a secret remain secret?
6. Why can a secret still be visible inside Docker even when Pulumi stores it encrypted?
7. Why should stack outputs be treated as a stable interface?
8. Why can changing the project name break configuration lookup?
9. Why must resources be destroyed before stack metadata is removed?
10. What additional isolation is required beyond separate stack names?

---

## Key Takeaways

- A project defines shared program logic; a stack is an isolated deployed instance.
- Stack state, configuration, secrets, outputs, and lifecycle are independent.
- Environment differences belong in configuration rather than duplicated source code.
- Required and typed getters turn configuration into an executable contract.
- Secret marking, encryption, and propagation reduce accidental disclosure but do not remove runtime exposure.
- Outputs carry asynchronous value, dependency, and secret metadata.
- `apply`, `interpolate`, and `all` are essential tools for safe output composition.
- Structured configuration improves organization but still requires validation.
- Secret rotation, stack destruction, and metadata removal are separate lifecycle operations.
- Production isolation requires secure backends and platform boundaries in addition to stack naming.

---

## Official References

- Pulumi Projects: <https://www.pulumi.com/docs/iac/concepts/projects/>
- Project File Reference: <https://www.pulumi.com/docs/iac/concepts/projects/project-file/>
- Pulumi Stacks: <https://www.pulumi.com/docs/iac/concepts/stacks/>
- Configuration: <https://www.pulumi.com/docs/iac/concepts/config/>
- Secrets: <https://www.pulumi.com/docs/iac/concepts/secrets/>
- Inputs and Outputs: <https://www.pulumi.com/docs/iac/concepts/inputs-outputs/>
- Stack Settings File: <https://www.pulumi.com/docs/iac/concepts/projects/stack-settings-file/>
- Docker Provider: <https://www.pulumi.com/registry/packages/docker/>
- Docker Container Resource: <https://www.pulumi.com/registry/packages/docker/api-docs/container/>

> Pulumi CLI behavior, provider schemas, and backend features can change. Validate the commands against the versions pinned in your repository before production deployment.
