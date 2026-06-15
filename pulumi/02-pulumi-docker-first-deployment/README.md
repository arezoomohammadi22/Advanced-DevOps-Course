# Pulumi Installation and First Docker Deployment

This guide provides a complete hands-on introduction to Pulumi using TypeScript and Docker. It begins by separating the responsibilities of the Pulumi CLI, Node.js runtime, Pulumi SDK, Docker provider, and Docker Engine. It then configures a local state backend, creates a real Pulumi project and stack, deploys an Nginx container, inspects outputs and state, performs updates, creates a second environment, introduces controlled drift, reconciles the deployment, troubleshoots common failures, and removes all managed resources safely.

Docker is used as the target platform because it makes the entire Pulumi lifecycle visible without requiring a public-cloud account or creating cloud costs. The same lifecycle applies later when the provider targets AWS, Azure, Google Cloud, Kubernetes, or another API-driven platform.

---

## Learning Outcomes

After completing this guide, you should be able to:

- Install and verify the Pulumi CLI on Linux, macOS, or Windows.
- Diagnose PATH problems and distinguish them from Pulumi project or provider errors.
- Explain the separate roles of the Pulumi CLI, Node.js runtime, Pulumi SDK, Docker provider package, provider plugin, and Docker Engine.
- Select a Pulumi backend and explain why a local backend is useful for a lab but normally insufficient for production collaboration.
- Create a TypeScript Pulumi project and a development stack.
- Read the purpose of `Pulumi.yaml`, `Pulumi.<stack>.yaml`, `index.ts`, `package.json`, `package-lock.json`, and `tsconfig.json`.
- Install and use `@pulumi/docker`.
- Define `docker.RemoteImage` and `docker.Container` resources.
- Use stack configuration instead of hard-coding environment-specific values.
- Run and interpret `pulumi preview`, `pulumi up`, `pulumi refresh`, and `pulumi destroy`.
- Distinguish create, update, replace, and delete operations.
- Read stack outputs, Pulumi URNs, and an exported state file.
- Create independent `dev` and `staging` stacks from one source program.
- Simulate Docker drift and restore the declared state.
- Apply a structured troubleshooting workflow.
- Add the project to Git without committing generated dependencies or state exports.

---

## Architecture of the Lab

The lab has several independent layers. Understanding them prevents errors from being blamed on the wrong component.

### Operating system and shell

The terminal executes commands and resolves binaries through `PATH`.

### Pulumi CLI

The CLI finds the project, selects the active stack, connects to the backend, starts the language runtime, launches previews and updates, coordinates providers, and writes new checkpoints.

### Node.js and TypeScript

Node.js executes the Pulumi program. TypeScript supplies static type checking and editor assistance. npm manages language packages.

### Pulumi SDK

`@pulumi/pulumi` provides the core programming model: configuration, outputs, resource registration, interpolation, project and stack identity, and common resource options.

### Docker provider package and provider plugin

`@pulumi/docker` provides TypeScript resource classes such as `docker.RemoteImage` and `docker.Container`. During deployment, Pulumi also uses the corresponding provider plugin to communicate with Docker.

### Docker Engine

Docker Engine is the actual target platform. It pulls images, creates containers, assigns IDs, and applies port mappings. Pulumi does not replace Docker; it manages Docker resources through Docker's API.

A failure in one layer should be tested at that layer. For example:

- `pulumi: command not found` is a CLI or PATH problem.
- A TypeScript import failure is normally a Node.js or npm dependency problem.
- A backend passphrase error is a state/secrets-provider problem.
- `Cannot connect to the Docker daemon` is a Docker connectivity or permission problem.
- A container creation failure can come from Docker, the image registry, port conflicts, or provider input.

---

## Practical Scenario

The goal is to run Nginx as a Pulumi-managed resource.

A manual workflow might use:

```bash
docker pull nginx:alpine
docker run --name pulumi-nginx-dev -p 8080:80 nginx:alpine
```

That creates a working container, but it does not provide a Pulumi stack, change preview, managed state, independent environment configuration, update history, or a consistent reconciliation workflow.

The Pulumi version of the deployment will define:

- An Nginx image resource
- An Nginx container resource
- A configurable host port
- A configurable physical container name
- A restart policy
- Stack outputs for the URL and provider-assigned identifiers
- Separate development and staging instances

---

## Prerequisites

Install the following:

- Pulumi CLI
- A supported Node.js LTS version
- npm
- Docker Engine or Docker Desktop
- Git, recommended
- A code editor, recommended

Verify every layer before creating the project:

```bash
pulumi version
node --version
npm --version
docker version
docker info
```

`docker version` should normally show both client and server information. If only the client appears, or the command cannot reach the daemon, the Pulumi Docker provider will also fail. Run an additional direct Docker test:

```bash
docker ps
```

Do not continue until Docker is working independently of Pulumi.

---

## Install the Pulumi CLI

### Linux

```bash
curl -fsSL https://get.pulumi.com | sh
```

The installation script normally places the CLI under `~/.pulumi/bin`. Open a new shell after installation. If the command is still unavailable, verify that the directory is in the active shell's `PATH`.

In a controlled organization, review remote installation scripts or install from an approved internal package repository.

### macOS

```bash
brew install pulumi/tap/pulumi
pulumi version
```

A future upgrade can be performed through Homebrew, but team environments should use a controlled CLI version strategy rather than allowing every workstation to upgrade independently.

### Windows

```powershell
winget install pulumi
pulumi version
```

Chocolatey or the official installer can also be used where appropriate. Avoid installing Pulumi through multiple package managers on the same host because several binaries may appear in different locations.

### Verify the active binary

```bash
# Linux or macOS
which pulumi
```

```powershell
# Windows PowerShell
where.exe pulumi
```

This command identifies the binary that the shell will execute. It is especially useful when the reported version is not the expected one.

---

## Why TypeScript Is Used

Pulumi supports TypeScript/JavaScript, Python, Go, .NET, Java, and YAML. TypeScript is used here because:

- Pulumi has extensive TypeScript examples.
- Static types catch many invalid resource inputs before deployment.
- npm makes provider package installation explicit.
- IDE completion makes provider schemas easier to explore.
- The language exposes the important distinction between ordinary values and `pulumi.Output` values.

The program is genuinely executed by Node.js, but it should primarily build a desired resource graph. Do not place unrelated side effects at the top level of a Pulumi program. Both preview and update execute the program, so arbitrary actions such as deleting files, modifying an external database, or sending messages could occur during preview as well.

---

## Select a State Backend

Pulumi stores a checkpoint for every stack. The checkpoint contains resource identities, inputs, outputs, dependencies, provider references, and the result of the last managed operation.

Common backend choices include:

- Pulumi Cloud
- Local filesystem
- Object storage such as S3-compatible storage
- Other supported self-managed backends

Pulumi Cloud is designed for team collaboration and can provide managed history, locking, access control, and visibility. A self-managed backend gives the organization more operational responsibility. A local backend is convenient for this isolated lab because it requires no external account, but it does not automatically provide team locking, shared access control, backup, or disaster recovery.

Connect the CLI to the local backend:

```bash
pulumi login --local
pulumi whoami -v
```

`pulumi whoami -v` verifies the current backend URL as well as the active identity/context.

> Treat backend selection as part of infrastructure architecture. If local state files are deleted, the Docker container may still exist while Pulumi loses its management history. Production state requires secure storage, encryption, backup, access control, concurrency protection, and a tested recovery procedure.

### Passphrase consideration

A local stack may use a passphrase-based secrets provider. Store the passphrase in a password manager. Losing it can make encrypted stack configuration unusable even when the state files still exist.

---

## Create the Project

```bash
mkdir pulumi-docker-lab
cd pulumi-docker-lab
pulumi new typescript
```

Use values similar to:

- Project name: `pulumi-docker-lab`
- Description: `First Pulumi Docker hands-on project`
- Stack name: `dev`

The command creates the project files and installs initial Node.js dependencies.

Expected structure:

```text
pulumi-docker-lab/
├── Pulumi.yaml
├── Pulumi.dev.yaml
├── index.ts
├── package.json
├── package-lock.json
├── tsconfig.json
└── node_modules/
```

The exact template can vary by CLI version, but the responsibilities remain the same.

---

## Understand the Project Files

### `Pulumi.yaml`

```yaml
name: pulumi-docker-lab
runtime: nodejs
description: First Pulumi Docker hands-on project
```

- `name` defines project identity.
- `runtime` tells Pulumi to execute the program using Node.js.
- `description` documents the project.

This file describes the project itself, not one environment.

### `Pulumi.dev.yaml`

This is the settings file for the `dev` stack. Values written with `pulumi config set` are stored here, using project-scoped keys by default. A future `staging` stack will have separate configuration, usually in `Pulumi.staging.yaml`.

### `index.ts`

This is the default TypeScript entry point. It executes during both preview and update and registers resources with the Pulumi engine.

### `package.json`

This file declares Node.js dependencies and scripts.

### `package-lock.json`

The lockfile records the exact dependency graph. Commit it to improve reproducibility. A provider upgrade should be a reviewable change because new versions can alter schemas, defaults, or diff behavior.

### `tsconfig.json`

This file configures TypeScript compilation.

### `node_modules/`

This directory contains installed packages and should not be committed. It can be rebuilt from `package-lock.json` using `npm ci`.

### Verify the active stack

```bash
pulumi stack
pulumi stack ls
```

Always verify the active stack before preview, update, refresh, or destroy. Running a correct command against the wrong environment is a common and serious operational failure.

---

## Install the Docker Provider

```bash
npm install @pulumi/docker
```

Verify the core and Docker packages:

```bash
npm list @pulumi/pulumi
npm list @pulumi/docker
```

The package changes should appear in `package.json` and `package-lock.json`.

---

## Write the Initial Pulumi Program

Replace `index.ts` with the following:

```typescript
import * as pulumi from "@pulumi/pulumi";
import * as docker from "@pulumi/docker";

const config = new pulumi.Config();

const hostPort = config.getNumber("hostPort") ?? 8080;
const containerName =
    config.get("containerName") ?? `pulumi-nginx-${pulumi.getStack()}`;

const nginxImage = new docker.RemoteImage("nginxImage", {
    name: "nginx:alpine",
    keepLocally: true,
});

const nginxContainer = new docker.Container("nginxContainer", {
    name: containerName,
    image: nginxImage.imageId,
    ports: [
        {
            internal: 80,
            external: hostPort,
            protocol: "tcp",
        },
    ],
    restart: "unless-stopped",
});

export const url = pulumi.interpolate`http://localhost:${hostPort}`;
export const containerId = nginxContainer.id;
export const imageId = nginxImage.imageId;
```

---

## Analyze the Program

### Imports

```typescript
import * as pulumi from "@pulumi/pulumi";
import * as docker from "@pulumi/docker";
```

The first package supplies the core Pulumi model. The second supplies Docker resource classes.

### Stack configuration

```typescript
const config = new pulumi.Config();

const hostPort = config.getNumber("hostPort") ?? 8080;
const containerName =
    config.get("containerName") ?? `pulumi-nginx-${pulumi.getStack()}`;
```

`getNumber` and `get` return optional values. The nullish-coalescing operator supplies defaults when no stack value exists.

`pulumi.getStack()` returns the current stack name. It helps produce a default physical container name that is different for `dev` and `staging`.

### Image resource

```typescript
const nginxImage = new docker.RemoteImage("nginxImage", {
    name: "nginx:alpine",
    keepLocally: true,
});
```

- `nginxImage` is the Pulumi logical name.
- `name` is the Docker image reference.
- `keepLocally` prevents Pulumi from removing the local image during resource deletion.

The Pulumi logical name is not the Docker image ID. Pulumi uses logical identity to track the resource in state.

### Container resource

```typescript
const nginxContainer = new docker.Container("nginxContainer", {
    name: containerName,
    image: nginxImage.imageId,
    ports: [
        {
            internal: 80,
            external: hostPort,
            protocol: "tcp",
        },
    ],
    restart: "unless-stopped",
});
```

The container input uses `nginxImage.imageId`, which is a provider output. This creates an implicit dependency: the container cannot be created until the image has been resolved or pulled and its ID is known.

The engine builds a dependency graph from these relationships. Source-code line order alone is not the complete execution model.

### Stack outputs

```typescript
export const url = pulumi.interpolate`http://localhost:${hostPort}`;
export const containerId = nginxContainer.id;
export const imageId = nginxImage.imageId;
```

Exports become stack outputs. They are stored as part of the stack contract and can be read by operators, CI pipelines, or another stack. `pulumi.interpolate` safely constructs a string that can include Pulumi-managed output values.

---

## Configure the Development Stack

```bash
pulumi stack
pulumi config set hostPort 8080
pulumi config set containerName pulumi-nginx-dev
pulumi config
```

The stack settings file should contain values similar to:

```yaml
config:
  pulumi-docker-lab:hostPort: "8080"
  pulumi-docker-lab:containerName: pulumi-nginx-dev
```

The values are namespaced by the project name. This reduces collisions when multiple components or providers define similarly named configuration keys.

Do not edit encrypted secret ciphertext manually. For ordinary configuration, the CLI is still preferred because it applies correct namespacing and type handling.

---

## Run the First Preview

```bash
pulumi preview --diff
```

The program executes, but Pulumi does not intentionally create the image or container during preview. The engine loads the empty or initial stack checkpoint, receives two resource declarations, calculates dependencies, asks the Docker provider for differences, and shows the proposed plan.

Expected operations include creation of:

- The Docker provider resource used internally by Pulumi
- `docker:index/remoteImage:RemoteImage`
- `docker:index/container:Container`

Review more than the summary count. Check:

- Resource types
- Logical names
- Image name
- Container name
- Port mapping
- Replacement indicators
- Deletes
- Sensitive or unexpected properties

A preview only improves safety when it is read.

---

## Deploy the Resources

```bash
pulumi up --diff
```

`pulumi up` shows the plan again, asks for confirmation in interactive mode, then executes provider operations according to the dependency graph.

Typical flow:

1. Resolve or pull the Nginx image.
2. Receive the image ID.
3. Create the container using that ID.
4. Write the new stack checkpoint.
5. Display stack outputs.

The first image pull can take longer. If the operation fails, inspect the provider diagnostic and test the lower layer directly. For example, verify that Docker itself can reach the registry.

Do not run concurrent updates against the same local stack. A shared production backend should provide appropriate concurrency controls.

---

## Validate the Deployment Outside Pulumi

Do not rely only on the IaC tool. Verify the real target platform:

```bash
docker ps --filter name=pulumi-nginx-dev
docker inspect pulumi-nginx-dev
curl http://localhost:8080
```

You can also open:

```text
http://localhost:8080
```

The default Nginx page confirms that the Docker resource exists and the port mapping works.

Read stack outputs:

```bash
pulumi stack output
pulumi stack output url
pulumi stack output containerId
```

A stack output is more than a log line. It is stored in state and can be consumed by automation. Sensitive outputs should be marked as secrets.

---

## Inspect Pulumi Resource Identity and State

Display resource URNs:

```bash
pulumi stack --show-urns
```

A Pulumi URN normally contains stack, project, type, and logical resource name. It is different from the Docker container ID.

Export the stack state for educational inspection:

```bash
pulumi stack export --file dev-state.json
```

Open `dev-state.json` and locate the image and container resources. Notice that state contains more than names:

- Inputs
- Outputs
- Dependencies
- Provider references
- URNs
- Physical IDs
- Metadata

Do not commit this export. State can contain sensitive operational data. Manual state editing is an advanced and risky operation. Delete the file after inspection or add it to `.gitignore`.

---

## Change the Host Port

Change development from port `8080` to `8081` without editing source code:

```bash
pulumi config set hostPort 8081
pulumi preview --diff
```

Inspect whether the Docker provider reports an in-place update or a replacement. Container port mappings commonly require recreation because Docker cannot modify every container property in place.

A replacement can create downtime. In a local lab the impact is minor, but in production it requires planning around traffic, health checks, load balancers, rollout strategy, and stateful data.

Apply the change:

```bash
pulumi up --diff
curl http://localhost:8081
curl http://localhost:8080
```

The new port should respond and the old port should no longer serve the same container.

Test idempotency:

```bash
pulumi preview
```

With no further code, configuration, or external changes, the preview should report no changes.

---

## Change the Image and Understand Mutable Tags

Temporarily modify the image resource:

```typescript
const nginxImage = new docker.RemoteImage("nginxImage", {
    name: "nginx:stable-alpine",
    keepLocally: true,
});
```

Then run:

```bash
pulumi preview --diff
pulumi up --diff
```

Because the container depends on `imageId`, an image identity change can also affect the container.

Tags such as `alpine`, `stable-alpine`, and `latest` are mutable. The registry may point the same tag to a new image while source code remains unchanged. For production reproducibility, prefer a controlled version or digest and make image upgrades explicit, reviewed changes.

Provider behavior for re-pulling a mutable tag can depend on resource options and provider implementation. Do not assume a tag is automatically re-resolved on every preview.

---

## Create an Independent Staging Stack

The same source code can create another environment with separate state and configuration. Avoid host conflicts by using a different port and container name.

```bash
pulumi stack init staging
pulumi config set hostPort 8082
pulumi config set containerName pulumi-nginx-staging
pulumi stack
pulumi preview --diff
pulumi up --diff
```

Creating the stack makes it active. Development configuration is not automatically copied.

Verify both environments:

```bash
pulumi stack ls
docker ps --filter name=pulumi-nginx
curl http://localhost:8081
curl http://localhost:8082
```

The important model is:

- One project and one source program
- Two independent stacks
- Two independent checkpoints
- Two independent configuration sets
- Two real Docker containers

A source-code commit does not automatically update every stack. Each stack changes only when the deployment workflow targets it.

---

## Introduce Controlled Drift

Return to development:

```bash
pulumi stack select dev
docker stop pulumi-nginx-dev
docker ps -a --filter name=pulumi-nginx-dev
```

The live container is now stopped, while the program and previously recorded state still represent the declared container resource.

Run a normal preview, then refresh:

```bash
pulumi preview
pulumi refresh --diff
```

A normal preview may not discover every live change because Pulumi does not necessarily perform a full provider refresh before every operation. A refresh explicitly reads live provider state and updates the recorded checkpoint.

After reviewing the refreshed state, reconcile the environment:

```bash
pulumi preview --diff
pulumi up --diff
docker ps --filter name=pulumi-nginx-dev
```

### More severe drift: external deletion

Delete the development container outside Pulumi:

```bash
docker rm -f pulumi-nginx-dev
pulumi refresh --diff
pulumi preview --diff
pulumi up --diff
```

Pulumi should detect the missing resource and recreate it during the update.

> Drift requires a decision. **Remediation** returns live state to code. **Adoption** changes code and state to accept the external change. Do not run refresh or update blindly in an incident because you may erase a valid emergency change or permanently accept an unauthorized one.

---

## Understand Create, Update, Replace, and Delete

### Create

Occurs when a declared resource has no managed state entry, such as the first deployment or a new stack.

### Update

Occurs when the provider can modify a property in place.

### Replace

Occurs when a changed property cannot be updated in place or the provider schema marks it as replacement-only. Replacement can mean create-before-delete or delete-before-create depending on resource behavior and options.

### Delete

Occurs when a managed resource is removed from the program or when the stack is destroyed.

These operations have different risk profiles. Always review replacements and deletes carefully. A replacement of a stateless development container is not equivalent to replacement of a production database.

To observe a proposed delete without applying it, temporarily remove or comment out the container declaration, run preview, study the plan, then restore the code before applying anything.

---

## Structured Troubleshooting

Troubleshoot from the lowest relevant layer upward:

1. CLI and `PATH`
2. Language runtime
3. npm dependencies
4. Backend and secrets provider
5. Active project and stack
6. Provider connectivity
7. Docker Engine
8. Registry/network access
9. Resource-specific configuration

### `pulumi: command not found`

```bash
# Linux or macOS
which pulumi
```

```powershell
# Windows
where.exe pulumi
```

Check whether the binary exists and whether the correct directory is in `PATH`. Opening a new terminal may be required. Reinstalling repeatedly without checking the path can create multiple versions.

### Cannot connect to Docker daemon

```bash
docker info
docker ps
```

If these commands fail, fix Docker first. On Linux, verify the service and Docker socket permissions. Membership in the `docker` group is security-sensitive because Docker access can provide high privilege on the host. Follow organizational policy rather than changing permissions casually.

On Docker Desktop, verify that the application is running and the correct Docker context is active.

### Port already allocated

List existing containers and ports:

```bash
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

Choose an unused port:

```bash
pulumi config set hostPort 8090
pulumi preview --diff
pulumi up --diff
```

A port conflict is a host-level error, not a Pulumi state error.

### `Module not found: @pulumi/docker`

Reinstall dependencies from the lockfile:

```bash
rm -rf node_modules
npm ci
```

On Windows, remove the directory using an appropriate PowerShell or Command Prompt command, then run `npm ci`.

Verify that `package.json` and `package-lock.json` are present and that the command is executed from the project directory.

### Local backend passphrase or secrets-provider failure

A passphrase error means encrypted configuration or stack metadata cannot be decrypted. Recover the correct passphrase from the approved password manager. Do not create a new passphrase and expect old ciphertext to decrypt.

Environment variables can be used in controlled automation, but they must be protected from shell history, process inspection, and CI logs.

### Interrupted or partial update

Do not immediately delete state files. Review:

```bash
pulumi stack
pulumi stack --show-urns
pulumi refresh --diff
pulumi preview --diff
```

Then determine whether to resume, repair, import, delete, or restore. The correct response depends on which provider operations completed.

### Wrong active stack

```bash
pulumi stack
pulumi stack ls
```

Stop before applying changes. Select the correct stack explicitly:

```bash
pulumi stack select dev
```

Production workflows should add CI/CD restrictions and approvals so sensitive stacks cannot be updated casually from a workstation.

---

## Add the Project to Git

Initialize the repository:

```bash
git init
printf "node_modules/
*.stack.json
dev-state.json
" >> .gitignore
git add .
git commit -m "Create first Pulumi Docker deployment"
```

Commit:

- `Pulumi.yaml`
- `Pulumi.<stack>.yaml` when it contains encrypted secrets rather than plaintext sensitive data and organizational policy permits it
- `index.ts`
- `package.json`
- `package-lock.json`
- `tsconfig.json`
- Documentation

Do not commit:

- `node_modules/`
- State exports
- Unencrypted secret files
- Temporary logs
- Local environment files containing credentials

Encrypted Pulumi configuration is safer than plaintext, but repository policy and backend security still matter.

---

## Extended Program with More Configuration

The following version allows the image name and restart policy to vary by stack:

```typescript
import * as pulumi from "@pulumi/pulumi";
import * as docker from "@pulumi/docker";

const config = new pulumi.Config();

const hostPort = config.getNumber("hostPort") ?? 8080;
const imageName = config.get("imageName") ?? "nginx:alpine";
const restartPolicy = config.get("restartPolicy") ?? "unless-stopped";
const containerName =
    config.get("containerName") ?? `pulumi-nginx-${pulumi.getStack()}`;

const image = new docker.RemoteImage("nginxImage", {
    name: imageName,
    keepLocally: true,
});

const container = new docker.Container("nginxContainer", {
    name: containerName,
    image: image.imageId,
    ports: [{ internal: 80, external: hostPort, protocol: "tcp" }],
    restart: restartPolicy,
});

export const containerNameOutput = container.name;
export const containerId = container.id;
export const imageId = image.imageId;
export const url = pulumi.interpolate`http://localhost:${hostPort}`;
```

Example configuration:

```bash
pulumi config set imageName nginx:alpine
pulumi config set restartPolicy unless-stopped
pulumi config
```

This design demonstrates a reusable program with environment-specific values stored outside the source logic.

---

## Clean Up Correctly

Destroy staging first:

```bash
pulumi stack select staging
pulumi destroy --diff
```

Destroy development:

```bash
pulumi stack select dev
pulumi destroy --diff
```

Verify that the resources are gone:

```bash
docker ps -a --filter name=pulumi-nginx
docker images nginx
```

The image can remain because `keepLocally: true` was configured.

Destroying resources does not automatically remove the stack record. Remove the stacks only after confirming that no managed resources remain and no state history is needed:

```bash
pulumi stack select staging
pulumi stack rm

pulumi stack select dev
pulumi stack rm
```

Removing a stack is a separate lifecycle operation from destroying its resources.

---

## Exercises

1. Add `imageName` to configuration and use different image tags in `dev` and `staging`.
2. Add `restartPolicy` to configuration.
3. Export the physical container name as a stack output.
4. Create a third stack named `test` using a unique port and container name.
5. Stop the staging container manually, refresh the stack, and explain the resulting diff.
6. Delete a container manually and restore it with Pulumi.
7. Temporarily remove the image resource from code and inspect the preview without applying it.
8. Change a logical resource name and observe the proposed delete/create behavior. Then investigate aliases before applying such a refactor.
9. Pin Nginx to a specific immutable version or digest and explain why it improves reproducibility.
10. Add a CI command that reads the `url` output and runs a smoke test.
11. Explain which files belong in Git and which files must remain local.
12. Write a recovery plan for a lost local backend.

---

## Review Questions

- Why is Docker the target platform rather than a replacement for Pulumi?
- Why does `docker.Container` depend on `docker.RemoteImage`?
- Why is changing a port potentially a replacement rather than an in-place update?
- Why can a normal preview miss live drift?
- What is the difference between the Pulumi URN and the Docker container ID?
- Why is a stack output different from a log message?
- Why should a mutable image tag be treated carefully?
- Why does one source program create two real environments without copying the code?
- What must be checked before destroying or removing a stack?
- Why is a local backend unsuitable as the default production choice?

---

## Key Takeaways

- Pulumi coordinates a language runtime, provider, backend, and target platform.
- Docker remains responsible for Docker resources; Pulumi manages their declared lifecycle.
- The project is shared source logic, while each stack owns independent configuration and state.
- Preview, update, refresh, and destroy serve different lifecycle purposes.
- Provider outputs create dependency relationships between resources.
- State is a management artifact and must not be treated as disposable.
- Configuration changes can cause replacement and real operational impact.
- Drift must be detected and reconciled intentionally.
- Validation should include both Pulumi output and direct target-platform checks.
- Safe cleanup requires destroying resources before removing stack records.

---

## Official References

- Pulumi Installation: <https://www.pulumi.com/docs/iac/download-install/>
- Pulumi CLI: <https://www.pulumi.com/docs/iac/cli/>
- Projects: <https://www.pulumi.com/docs/iac/concepts/projects/>
- Stacks: <https://www.pulumi.com/docs/iac/concepts/stacks/>
- State and Backends: <https://www.pulumi.com/docs/iac/concepts/state-and-backends/>
- Configuration and Secrets: <https://www.pulumi.com/docs/iac/concepts/config/>
- Docker Provider: <https://www.pulumi.com/registry/packages/docker/>
- Docker `RemoteImage`: <https://www.pulumi.com/registry/packages/docker/api-docs/remoteimage/>
- Docker `Container`: <https://www.pulumi.com/registry/packages/docker/api-docs/container/>
- Drift Detection: <https://www.pulumi.com/docs/deployments/deployments/drift/>

> CLI behavior, provider schemas, and Docker resource properties can change. Review the documentation for the versions used by your project before applying the workflow to production infrastructure.
