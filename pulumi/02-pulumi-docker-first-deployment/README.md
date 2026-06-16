# Pulumi YAML Docker Infrastructure Lab

This project demonstrates how to install Pulumi on Ubuntu 24.04, verify or install Docker Engine, configure a local Pulumi backend, and manage a complete Nginx service with the Pulumi Docker provider.

The infrastructure is authored in **Pulumi YAML**. TypeScript and Python equivalents are included only to show that Pulumi can express the same resources through multiple language frontends.

The project manages the following Docker resources:

- A dedicated bridge network
- An Nginx image pulled from a registry
- An Nginx container attached to the dedicated network
- A configurable host-to-container port mapping
- A read-only bind mount containing a custom web page
- A Docker restart policy
- Stack outputs containing the application URL and resource identifiers

The full lifecycle covered by this guide is:

```text
Environment verification
        ↓
Pulumi CLI installation
        ↓
Docker Client and Daemon verification
        ↓
Local Pulumi backend
        ↓
Pulumi YAML project and dev stack
        ↓
Docker Network + Remote Image + Container
        ↓
pulumi preview
        ↓
pulumi up
        ↓
Pulumi, Docker, and HTTP validation
        ↓
Configuration update and idempotency test
        ↓
Drift simulation, refresh, and recovery
        ↓
State export
        ↓
pulumi destroy and cleanup validation
```

---

## Table of Contents

- [What This Project Teaches](#what-this-project-teaches)
- [Architecture](#architecture)
- [Pulumi YAML, Docker Compose, TypeScript, and Python](#pulumi-yaml-docker-compose-typescript-and-python)
- [Requirements](#requirements)
- [Verify the Ubuntu Environment](#verify-the-ubuntu-environment)
- [Install Pulumi CLI](#install-pulumi-cli)
- [Verify Docker](#verify-docker)
- [Install Docker Engine on Ubuntu 24.04](#install-docker-engine-on-ubuntu-2404)
- [Allow the Current User to Access Docker](#allow-the-current-user-to-access-docker)
- [Configure a Local Pulumi Backend](#configure-a-local-pulumi-backend)
- [Create the Pulumi YAML Project](#create-the-pulumi-yaml-project)
- [Create the Web Content](#create-the-web-content)
- [Configure the Stack](#configure-the-stack)
- [Complete Pulumi YAML Program](#complete-pulumi-yaml-program)
- [Understand the Resource Model](#understand-the-resource-model)
- [Preview the Deployment](#preview-the-deployment)
- [Deploy the Infrastructure](#deploy-the-infrastructure)
- [Validate the Result](#validate-the-result)
- [Test Idempotency](#test-idempotency)
- [Update the Host Port](#update-the-host-port)
- [Update the Image](#update-the-image)
- [Understand Bind-Mount Content Changes](#understand-bind-mount-content-changes)
- [Simulate and Repair Drift](#simulate-and-repair-drift)
- [Export a State Backup](#export-a-state-backup)
- [Destroy the Infrastructure](#destroy-the-infrastructure)
- [Create a Second Stack](#create-a-second-stack)
- [Troubleshooting](#troubleshooting)
- [Equivalent TypeScript and Python Resources](#equivalent-typescript-and-python-resources)
- [Security and Production Notes](#security-and-production-notes)
- [Recommended Repository Files](#recommended-repository-files)
- [Official Documentation](#official-documentation)

---

## What This Project Teaches

After completing the project, you should be able to:

1. Install and verify the Pulumi CLI on Ubuntu 24.04.
2. Verify Docker from the client, daemon, registry, and container-runtime perspectives.
3. Explain why the Pulumi Docker provider requires access to the Docker API.
4. Use a local backend to store Pulumi stack state.
5. Create a Pulumi project and an independent `dev` stack.
6. Define configuration values separately from infrastructure code.
7. Define Docker resources in `Pulumi.yaml`.
8. Understand dependencies created by Pulumi output references.
9. Read the output of `pulumi preview` before applying changes.
10. Deploy and verify a Docker network, image, container, port mapping, and bind mount.
11. Test idempotency by running the same program multiple times.
12. Observe update or replacement behavior after changing configuration.
13. Simulate configuration drift by deleting a resource outside Pulumi.
14. Reconcile recorded state with actual Docker state using `pulumi refresh`.
15. Recreate a missing resource with `pulumi up`.
16. Export a stack-state backup safely.
17. Delete managed resources in dependency-aware order with `pulumi destroy`.

---

## Architecture

The project uses this execution path:

```text
Pulumi.yaml + Pulumi.dev.yaml
              ↓
       Pulumi YAML Runtime
              ↓
 Pulumi Engine: graph, state, and diff
              ↓
      Docker Provider Plugin
              ↓
       Docker API over socket
              ↓
         Docker Daemon
              ↓
 Network + Remote Image + Nginx Container
              ↓
 Host port 8080 → Container port 80
              ↓
       Custom read-only index.html
```

On a standard Linux Docker installation, the Docker client and the Pulumi Docker provider normally communicate with the daemon through:

```text
/var/run/docker.sock
```

Pulumi does **not** replace Docker Engine. Pulumi manages the desired lifecycle of Docker resources, while Docker Engine performs the actual image, network, container, mount, and port operations.

A simplified deployment flow is:

```text
1. Pulumi CLI identifies the current project and stack.
2. The YAML runtime reads Pulumi.yaml and stack configuration.
3. Resources are registered with the Pulumi engine.
4. The engine creates a dependency graph.
5. The engine compares desired resources with recorded state.
6. The Docker provider validates and applies Docker operations.
7. Docker Engine creates the real resources.
8. Provider outputs are returned to the engine.
9. Pulumi writes a new state checkpoint.
10. Stack outputs are displayed.
```

---

## Pulumi YAML, Docker Compose, TypeScript, and Python

### Pulumi YAML is not Docker Compose

Both tools use YAML syntax, but they use different schemas and different lifecycle models.

A Docker Compose service may look like this:

```yaml
services:
  web:
    image: nginx:alpine
```

A Pulumi YAML resource uses a Pulumi resource type:

```yaml
resources:
  nginxImage:
    type: docker:RemoteImage
    properties:
      name: nginx:alpine
```

With Pulumi:

- Each managed object is a Pulumi resource.
- Each resource receives a logical identity and a URN.
- Resource inputs and outputs are stored in stack state.
- Dependencies are derived from output references.
- Preview, update, refresh, import, and destroy are state-aware operations.
- A provider plugin translates Pulumi resource operations into Docker API operations.

### Why use YAML here?

Pulumi YAML allows infrastructure to be defined without requiring a Node.js or Python runtime for the Pulumi program itself. It is useful for teams that already understand YAML and want to begin with a declarative authoring model.

The same Docker resources can also be authored with TypeScript, Python, Go, .NET, or Java. The authoring syntax changes, but the engine, state model, provider, and Docker API remain conceptually the same.

---

## Requirements

Use an Ubuntu 24.04 LTS host with:

- A regular user account
- `sudo` access
- Internet connectivity
- DNS and HTTPS access
- Enough disk space for Docker images
- An available TCP port such as `8080`

The guide assumes Bash as the shell.

Docker may already be installed. If it is installed and working, skip the installation section and continue with verification.

---

## Verify the Ubuntu Environment

Check the operating system, architecture, user, groups, and working directory:

```bash
cat /etc/os-release
uname -m
whoami
id
pwd
```

Expected observations:

- `/etc/os-release` should identify Ubuntu 24.04.
- The codename is normally `noble`.
- `uname -m` commonly returns `x86_64` or `aarch64`.
- `id` shows the current user's group memberships.

Verify that `sudo` authentication works:

```bash
sudo -v
```

This validates credentials and refreshes the current sudo timestamp without changing infrastructure.

Check outbound HTTPS access:

```bash
curl -I https://get.pulumi.com
curl -I https://download.docker.com
```

These requests retrieve response headers only. If they fail, resolve DNS, proxy, routing, firewall, or certificate problems before continuing.

---

## Install Pulumi CLI

Install Pulumi with the official installation script:

```bash
curl -fsSL https://get.pulumi.com | sh
```

### What this command does

- `curl` downloads the official installation script.
- `-f` fails on HTTP errors.
- `-s` reduces unnecessary output.
- `-S` still displays errors.
- `-L` follows redirects.
- The downloaded script is passed to the shell.
- The installer detects the system architecture.
- Pulumi binaries are installed under the current user's home directory, normally in `~/.pulumi/bin`.

At this point:

- No Pulumi backend has been selected.
- No project exists.
- No stack exists.
- No provider has been installed or executed.
- No Docker resource has been created.

### Security note about pipe-to-shell installation

Piping a downloaded script directly to a shell is convenient for a lab. In a controlled production environment, download and inspect the script first, or use official binaries and verify their published checksums.

### Add Pulumi to `PATH` if required

```bash
export PATH="$HOME/.pulumi/bin:$PATH"
echo 'export PATH="$HOME/.pulumi/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

The first command affects the current shell. The second persists the setting for future Bash shells. The third reloads the Bash configuration without requiring logout and login.

### Verify the installation

```bash
command -v pulumi
pulumi version
pulumi help | head -n 20
```

`command -v pulumi` should return a valid executable path. The version number may differ from screenshots or classroom examples because Pulumi releases change over time.

If Bash reports `pulumi: command not found`, fix `PATH`; this error is unrelated to Docker or the Docker provider.

---

## Verify Docker

Pulumi's Docker provider requires a reachable Docker daemon. Verify the Docker client and daemon before creating a Pulumi project.

```bash
docker version
sudo systemctl is-active docker
sudo systemctl status docker --no-pager
```

Interpretation:

- `docker version` attempts to display both Client and Server information.
- If only Client information appears, the CLI exists but the daemon may be stopped or inaccessible.
- `systemctl is-active docker` should return `active`.
- `systemctl status` provides process, startup, and recent log information.

Perform an end-to-end Docker test:

```bash
docker info
docker run --rm hello-world
```

A successful `hello-world` run validates the complete path:

```text
Docker CLI
   ↓
Docker socket
   ↓
Docker daemon
   ↓
Registry access
   ↓
Image pull
   ↓
Container creation
   ↓
Container runtime execution
```

The `--rm` option removes the temporary container after it exits.

If you receive a socket permission error, continue to [Allow the Current User to Access Docker](#allow-the-current-user-to-access-docker).

---

## Install Docker Engine on Ubuntu 24.04

Skip this section when Docker Engine is already installed and healthy.

Remove packages that can conflict with Docker's official packages:

```bash
sudo apt remove -y \
  docker.io \
  docker-compose \
  docker-compose-v2 \
  docker-doc \
  podman-docker \
  containerd \
  runc || true
```

Removing conflicting packages does not automatically remove Docker data under `/var/lib/docker`. However, do not perform package replacement on a production host without understanding the existing installation and creating appropriate backups.

Install prerequisites:

```bash
sudo apt update
sudo apt install -y ca-certificates curl
```

Create the keyring directory and install Docker's repository key:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

Add Docker's official APT source:

```bash
sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

Install Docker Engine and related plugins:

```bash
sudo apt update
sudo apt install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin
```

Enable and start Docker:

```bash
sudo systemctl enable --now docker
sudo systemctl is-active docker
```

Run a privileged verification test before changing user permissions:

```bash
sudo docker run --rm hello-world
```

---

## Allow the Current User to Access Docker

The Pulumi CLI should normally be executed as the regular project user, not with `sudo`. The Docker provider therefore needs that user to be able to access the Docker socket.

Create or locate the Docker group and add the current user:

```bash
getent group docker || sudo groupadd docker
sudo usermod -aG docker "$USER"
```

Apply the new group membership either by logging out and back in, or by starting a shell with the new primary group:

```bash
newgrp docker
```

Test Docker without `sudo`:

```bash
docker run --rm hello-world
```

Inspect the socket and user groups:

```bash
ls -l /var/run/docker.sock
id
docker info --format 'Server Version: {{.ServerVersion}}'
```

Typical socket ownership is:

```text
root:docker
```

The current user should appear as a member of the `docker` group.

> **Important:** Membership in the `docker` group is effectively root-equivalent access to the host. A user with Docker access can create privileged containers or mount sensitive host paths. Use this setup only when it matches your security model. Evaluate Rootless Docker or stricter access controls for production systems.

Avoid running normal Pulumi commands with `sudo`. Doing so can create root-owned state, plugin, or project files and can make later non-root operation confusing.

---

## Configure a Local Pulumi Backend

Pulumi requires state to track managed resources. State includes:

- Resource URNs
- Provider resource IDs
- Inputs and outputs
- Dependencies
- Stack outputs
- The last successful checkpoint

Use a local file-based backend for this lab:

```bash
pulumi login --local
pulumi whoami
```

This command selects the local backend for stacks created afterward. It does not create any Docker resource.

Conceptually:

```text
Pulumi CLI
    ↓
pulumi login --local
    ↓
Local state backend
    ↓
Project and stack checkpoints
    ↓
Docker IDs, inputs, outputs, and dependencies
```

### Passphrase note

A local backend commonly uses a passphrase-based secrets provider. Pulumi may request a passphrase when creating a stack. Store it securely. Even when this project contains no real secret, the stack still has a secrets-provider configuration.

A local backend is suitable for learning and single-user experiments. A team environment normally requires a shared backend, backups, access control, concurrency protection, and an operational recovery plan.

---

## Create the Pulumi YAML Project

Create the project directory:

```bash
mkdir -p ~/labs/pulumi-docker-yaml-lab
cd ~/labs/pulumi-docker-yaml-lab
```

Create a Pulumi YAML project and the initial `dev` stack:

```bash
pulumi new yaml \
  --name pulumi-docker-yaml-lab \
  --description "Docker infrastructure with Pulumi YAML" \
  --stack dev
```

If the command runs interactively, use:

- Project name: `pulumi-docker-yaml-lab`
- Description: `Docker infrastructure with Pulumi YAML`
- Stack name: `dev`

If a passphrase is requested, choose one for the lab and store it safely.

Verify the generated project:

```bash
pwd
ls -la
cat Pulumi.yaml
pulumi stack ls
pulumi stack
```

At this stage:

- `Pulumi.yaml` should exist in the project root.
- `runtime: yaml` tells Pulumi to use the YAML runtime.
- The `dev` stack exists.
- No custom Docker resource has been deployed yet.

### Project and stack relationship

A **project** represents the infrastructure program, commonly stored in one repository.

A **stack** is an independently configured and independently stateful instance of that project. The same project can be deployed as:

```text
dev
staging
production
```

Each stack can have different ports, names, image tags, paths, and secrets.

---

## Create the Web Content

Create the bind-mounted Nginx content:

```bash
mkdir -p html

cat > html/index.html <<'EOF'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Pulumi Docker YAML Lab</title>
  <style>
    body {
      font-family: sans-serif;
      max-width: 760px;
      margin: 80px auto;
    }

    code {
      background: #eef2f5;
      padding: 3px 6px;
    }
  </style>
</head>
<body>
  <h1>Hello from Pulumi YAML</h1>
  <p>This Nginx container is managed by Pulumi.</p>
  <p>Provider: <code>docker</code> | Stack: <code>dev</code></p>
</body>
</html>
EOF
```

List project files:

```bash
find . -maxdepth 2 -type f -print
```

Verify that the file is readable:

```bash
cat html/index.html
test -r html/index.html && echo "HTML file is readable"
```

At this point Nginx is not running, so an HTTP request to the future application port should not yet return the application page.

The HTML file is application content, not a separate Pulumi resource. Pulumi will configure Docker to mount its directory into the container.

---

## Configure the Stack

The program will support four configuration values:

| Configuration | Type | Purpose | Default |
|---|---:|---|---|
| `appName` | string | Physical naming prefix | `pulumi-nginx` |
| `imageName` | string | Nginx image reference | `nginx:alpine` |
| `hostPort` | integer | Published port on the Ubuntu host | `8080` |
| `webRoot` | string | Absolute host path mounted into Nginx | Required |

Store stack-specific values:

```bash
pulumi config set webRoot "$(pwd)/html"
pulumi config set hostPort 8080
```

Inspect configuration:

```bash
pulumi config
cat Pulumi.dev.yaml
```

`pulumi config set` updates configuration for the currently selected stack. It does not execute the infrastructure program and does not change Docker resources.

The stack file may contain namespaced keys similar to:

```yaml
config:
  pulumi-docker-yaml-lab:hostPort: "8080"
  pulumi-docker-yaml-lab:webRoot: /home/example/labs/pulumi-docker-yaml-lab/html
```

The exact path depends on the current user's home directory.

`webRoot` must be an absolute path because Docker bind mounts resolve paths on the Docker host.

---

## Complete Pulumi YAML Program

Replace the generated `Pulumi.yaml` with the complete program:

```bash
cat > Pulumi.yaml <<'EOF'
name: pulumi-docker-yaml-lab
runtime: yaml
description: Docker infrastructure managed with Pulumi YAML

config:
  appName:
    type: string
    default: pulumi-nginx

  imageName:
    type: string
    default: nginx:alpine

  hostPort:
    type: integer
    default: 8080

  webRoot:
    type: string

resources:
  appNetwork:
    type: docker:Network
    properties:
      name: ${appName}-network
      driver: bridge

  nginxImage:
    type: docker:RemoteImage
    properties:
      name: ${imageName}
      keepLocally: false

  webContainer:
    type: docker:Container
    properties:
      name: ${appName}
      image: ${nginxImage.imageId}
      restart: unless-stopped
      envs:
        - APP_ENV=training
      networksAdvanced:
        - name: ${appNetwork.name}
          aliases:
            - web
      ports:
        - internal: 80
          external: ${hostPort}
          ip: 0.0.0.0
          protocol: tcp
      volumes:
        - hostPath: ${webRoot}
          containerPath: /usr/share/nginx/html
          readOnly: true

outputs:
  applicationUrl: http://localhost:${hostPort}
  containerName: ${webContainer.name}
  containerId: ${webContainer.id}
  imageId: ${nginxImage.imageId}
  networkName: ${appNetwork.name}
EOF
```

Review the final file:

```bash
sed -n '1,220p' Pulumi.yaml
```

YAML is indentation-sensitive. Use spaces, not tab characters.

---

## Understand the Resource Model

### Project metadata and runtime

```yaml
name: pulumi-docker-yaml-lab
runtime: yaml
```

- `name` identifies the Pulumi project.
- The project name becomes part of resource URNs.
- `runtime: yaml` selects the Pulumi YAML runtime.
- The YAML program does not require a Node.js or Python runtime.

### Configuration declarations

```yaml
config:
  appName:
    type: string
    default: pulumi-nginx
```

The `config` section declares accepted program configuration. Defaults are used unless the current stack overrides them.

`webRoot` has no default and is therefore required. A missing value should cause preview to fail instead of deploying an invalid mount.

### Docker network

```yaml
appNetwork:
  type: docker:Network
  properties:
    name: ${appName}-network
    driver: bridge
```

- `appNetwork` is the **logical name** inside the Pulumi program.
- `${appName}-network` becomes the **physical Docker network name**.
- `docker:Network` selects the Docker provider's Network resource.
- `bridge` creates a private network on the local Docker host.

Changing a Pulumi logical name can change resource identity. Without an alias, Pulumi may interpret the renamed logical resource as a new resource even when the physical name remains similar.

### Remote image

```yaml
nginxImage:
  type: docker:RemoteImage
  properties:
    name: ${imageName}
    keepLocally: false
```

The remote image resource manages an image on the Docker host.

- The default image reference is `nginx:alpine`.
- The provider pulls the image when required.
- `imageId` is an output produced by the provider.
- `keepLocally: false` allows removal during destroy when Docker and provider constraints permit it.

An image can remain on the host when it is still referenced or used elsewhere. Always inspect the actual destroy output.

### Container identity and dependency on the image

```yaml
webContainer:
  type: docker:Container
  properties:
    name: ${appName}
    image: ${nginxImage.imageId}
```

`${nginxImage.imageId}` serves two purposes:

1. It passes the exact image identifier to the container.
2. It creates a dependency from the container to the image resource.

The engine therefore knows that the container cannot be created until the image output is available.

### Restart policy

```yaml
restart: unless-stopped
```

Docker Engine enforces the restart policy. Pulumi does not run a continuous monitoring loop for this behavior.

### Environment variables

```yaml
envs:
  - APP_ENV=training
```

This configures an environment variable inside the container. It can be inspected later through `docker inspect`.

### Network attachment and alias

```yaml
networksAdvanced:
  - name: ${appNetwork.name}
    aliases:
      - web
```

The container depends on the network because it references `${appNetwork.name}`.

The alias `web` can be resolved by other containers attached to the same Docker network. This project uses one container, but the alias demonstrates Docker network service discovery.

### Port mapping

```yaml
ports:
  - internal: 80
    external: ${hostPort}
    ip: 0.0.0.0
    protocol: tcp
```

- Nginx listens on port `80` inside the container.
- `${hostPort}` is published on the Ubuntu host.
- `0.0.0.0` binds the port on all IPv4 interfaces.
- The protocol is TCP.

For a host-local-only service, consider binding to `127.0.0.1`. When using `0.0.0.0` on a remote server, review host firewall and cloud security-group rules.

### Read-only bind mount

```yaml
volumes:
  - hostPath: ${webRoot}
    containerPath: /usr/share/nginx/html
    readOnly: true
```

Docker mounts the host directory directly into Nginx's document root.

- Pulumi does not copy `index.html` into the container.
- Docker configures the bind mount at container creation.
- `readOnly: true` prevents the container from modifying the host directory through this mount.

### Stack outputs

```yaml
outputs:
  applicationUrl: http://localhost:${hostPort}
  containerName: ${webContainer.name}
  containerId: ${webContainer.id}
  imageId: ${nginxImage.imageId}
  networkName: ${appNetwork.name}
```

Some outputs are known from configuration. Provider-generated outputs such as resource IDs remain unknown until creation is complete. After a successful update, Pulumi stores them in stack state.

---

## Preview the Deployment

Run a preview before changing Docker:

```bash
pulumi preview
```

The preview flow is:

```text
Load Pulumi.yaml and Pulumi.dev.yaml
             ↓
Resolve configuration and expressions
             ↓
Register Network, RemoteImage, and Container
             ↓
Build the dependency graph
             ↓
Load current stack state
             ↓
Ask the Docker provider to validate and calculate differences
             ↓
Display Create, Update, Replace, or Delete operations
```

For a new stack, expect create operations for:

- `docker:Network`
- `docker:RemoteImage`
- `docker:Container`

You may also see the Pulumi stack resource in the graph.

Preview is a plan, not the final deployment. Provider plugins may still be downloaded, and providers may perform limited reads or validation. Preview should not be treated as a completely offline parser.

Inspect installed plugins and the current stack:

```bash
pulumi plugin ls
pulumi stack --show-urns
```

After preview alone, the three Docker resources should not yet be recorded as successfully created.

### Common preview failures

- Docker socket permission denied
- Required `webRoot` configuration missing
- Invalid YAML indentation
- Invalid provider property
- Plugin download failure
- Registry or Internet connectivity problems
- Invalid path or unavailable host environment

Read the first meaningful error message before proceeding to `pulumi up`.

---

## Deploy the Infrastructure

Apply the desired state:

```bash
pulumi up
```

Pulumi reruns the program, calculates a plan, and asks for confirmation. Review the resource summary and confirm the update.

### What happens behind the scenes

1. The CLI identifies the current project and selected stack.
2. The engine reads the previous checkpoint from the local backend.
3. The YAML runtime resolves stack configuration.
4. The runtime sends resource registrations to the engine.
5. The engine creates URNs from stack, project, type, and logical name.
6. The engine builds the dependency graph.
7. The Docker provider sends a network-create request to the Docker API.
8. The Docker provider pulls or reads the configured image.
9. The provider returns the image ID to the engine.
10. The engine resolves the container's image and network inputs.
11. The provider asks Docker Engine to create the container.
12. Docker configures the network attachment, environment, restart policy, port binding, and bind mount.
13. Docker starts Nginx inside the container.
14. The provider returns the container ID and other outputs.
15. Pulumi writes a successful state checkpoint.
16. Stack outputs are printed.

The network and image do not depend on each other, so the engine may process them in parallel. The container depends on both and must wait for their outputs.

Pulumi Engine does not simply execute a hidden `docker run` command. It sends typed resource operations to the Docker provider, which communicates with the Docker API.

---

## Validate the Result

Do not accept a deployment only because `pulumi up` reports success. Validate it from three independent perspectives.

### 1. Validate Pulumi state and outputs

```bash
pulumi stack
pulumi stack output
pulumi stack output applicationUrl
pulumi stack --show-ids --show-urns
```

These commands verify that Pulumi recorded the update, resource identities, and outputs.

### 2. Validate Docker resources

```bash
docker ps --filter name=pulumi-nginx
docker image ls nginx
docker network ls --filter name=pulumi-nginx-network
docker inspect pulumi-nginx
docker network inspect pulumi-nginx-network
```

Inspect specific properties:

```bash
docker inspect pulumi-nginx \
  --format '{{json .HostConfig.RestartPolicy}}'

docker inspect pulumi-nginx \
  --format '{{json .Mounts}}'

docker inspect pulumi-nginx \
  --format '{{json .NetworkSettings.Ports}}'
```

You should confirm:

- The container is in the `Up` state.
- The Nginx image exists.
- The custom bridge network exists.
- The container is attached to that network.
- Port `8080` maps to container port `80/tcp`.
- The host HTML directory is mounted read-only.
- The restart policy is `unless-stopped`.

### 3. Validate the application over HTTP

```bash
curl -i http://127.0.0.1:8080
```

Perform an assertion-style test:

```bash
curl -fsS http://127.0.0.1:8080 \
  | grep "Hello from Pulumi YAML"
```

A successful response verifies the complete application path:

```text
Host TCP port
   ↓
Docker port publishing
   ↓
Container network namespace
   ↓
Nginx process
   ↓
Read-only bind-mounted index.html
```

A valid result requires all of the following:

- Pulumi lists the managed resources.
- Docker shows the container in the `Up` state.
- The network contains the container.
- The port mapping is correct.
- HTTP returns the custom page.

---

## Test Idempotency

Run the same desired state again without changing the program or configuration:

```bash
pulumi preview
pulumi up
```

Expected result:

```text
No changes
```

Pulumi matches the current registrations with existing resource URNs and recorded state. The provider finds no effective difference, so Pulumi should not create duplicate containers or networks.

Verify that only one matching container exists:

```bash
docker ps -a \
  --filter name=pulumi-nginx \
  --format 'table {{.ID}}\t{{.Names}}\t{{.Status}}'
```

This demonstrates that Pulumi is not a shell script that blindly creates new resources each time it runs.

---

## Update the Host Port

Change the `dev` stack's host port from `8080` to `8081`:

```bash
pulumi config set hostPort 8081
pulumi preview
```

Read the preview carefully. Docker port bindings are part of container creation configuration, so the provider may require replacement of the container. The preview is the authoritative source.

Typical desired behavior:

- The network remains unchanged.
- The image remains unchanged.
- The container is updated or replaced.
- The new stack output uses port `8081`.

Apply the change:

```bash
pulumi up
```

Validate the new port:

```bash
curl -fsS http://127.0.0.1:8081 \
  | grep "Hello from Pulumi YAML"
```

Verify that the previous port no longer responds:

```bash
! curl -fsS http://127.0.0.1:8080 >/dev/null
```

Check the updated output:

```bash
pulumi stack output applicationUrl
```

This experiment demonstrates minimal change: Pulumi changes only resources affected by the new input.

---

## Update the Image

Change the image configuration:

```bash
pulumi config set imageName nginx:stable-alpine
pulumi preview
pulumi up
```

Changing the image reference affects the `RemoteImage` resource. A new image ID can then propagate into the container because the container uses:

```yaml
image: ${nginxImage.imageId}
```

This demonstrates that dependencies are not only about creation order. A changed output can also trigger an update or replacement in a dependent resource.

Verify the configured image:

```bash
docker inspect pulumi-nginx --format '{{.Config.Image}}'
docker image ls nginx
```

---

## Understand Bind-Mount Content Changes

Modify the file mounted into Nginx:

```bash
sed -i \
  's/Hello from Pulumi YAML/Updated without replacing the container/' \
  html/index.html
```

Test the page:

```bash
curl -fsS http://127.0.0.1:8081 \
  | grep 'Updated without replacing the container'
```

Run a preview:

```bash
pulumi preview
```

Pulumi will normally show no infrastructure change because the container input contains the **path** of the bind mount, not a hash of the directory contents.

The file changes immediately inside the running container because Docker exposes the host directory directly.

This is an important ownership boundary:

- Pulumi manages the mount configuration.
- Docker provides the bind mount.
- The current program does not version or hash the mounted files.

For immutable content delivery, build a custom image or introduce an explicit content-version trigger.

---

## Simulate and Repair Drift

Create drift by deleting the container outside Pulumi:

```bash
docker rm -f pulumi-nginx
```

Confirm that Docker no longer has the container:

```bash
docker ps -a --filter name=pulumi-nginx
```

Pulumi's last checkpoint may still record the container because external deletion does not automatically rewrite Pulumi state.

Inspect the current stack:

```bash
pulumi stack
```

### Refresh the recorded state

```bash
pulumi refresh
```

`pulumi refresh` asks the Docker provider to read actual resources and updates Pulumi's recorded state to reflect reality.

Refresh does **not** reapply `Pulumi.yaml`. It synchronizes recorded state with the provider's actual state.

Preview the desired recovery:

```bash
pulumi preview
```

Pulumi should now plan to recreate the missing container.

Reapply the desired state:

```bash
pulumi up
```

Validate the recovered service:

```bash
docker ps --filter name=pulumi-nginx
curl -fsS http://127.0.0.1:8081
```

The relationship is:

```text
Pulumi.yaml       = desired state
Pulumi checkpoint = recorded state
Docker Engine     = actual state
```

Drift exists when recorded or desired state no longer matches actual provider state.

---

## Export a State Backup

Export the current stack state:

```bash
pulumi stack export > stack-backup.json
ls -lh stack-backup.json
head -n 30 stack-backup.json
```

The exported file can be useful for backup, migration, and troubleshooting.

Important rules:

- Do not edit state casually with a text editor.
- A malformed state file can break resource tracking.
- State can include sensitive metadata.
- Encrypted secrets may still be present as ciphertext.
- Do not commit `stack-backup.json` to a public repository.

---

## Destroy the Infrastructure

Delete all custom resources managed by the current stack:

```bash
pulumi destroy
```

Pulumi reads state and deletes resources in reverse dependency order. The container must be removed before resources it depends on.

Conceptual order:

```text
Read stack state
       ↓
Build reverse dependency order
       ↓
Delete webContainer
       ↓
Delete appNetwork
       ↓
Delete managed RemoteImage when possible
       ↓
Write an empty-resource checkpoint
```

Validate cleanup:

```bash
docker ps -a --filter name=pulumi-nginx
docker network ls --filter name=pulumi-nginx-network
pulumi stack
```

The container and network should be absent. The image may remain when Docker or provider constraints prevent removal, or when another object uses it.

The stack still exists after destroy, but it contains no custom managed resources.

Remove the empty stack when it is no longer required:

```bash
pulumi stack rm dev
```

Do not remove a stack while real managed resources still exist unless you intentionally accept orphaned resources and understand the consequences.

Removing a stack does not delete the project files from disk.

---

## Create a Second Stack

A project can have multiple independent stacks. Create a `test` stack using the same `Pulumi.yaml`:

```bash
pulumi stack init test
pulumi config set appName pulumi-nginx-test
pulumi config set hostPort 8090
pulumi config set webRoot "$(pwd)/html"
pulumi up
```

Because `dev` and `test` use the same Docker host, they must use different physical names and host ports to avoid conflicts.

Inspect stacks and switch between them:

```bash
pulumi stack ls
pulumi stack select dev
pulumi stack select test
```

Each stack has independent:

- Configuration
- State
- Resource IDs
- Outputs
- Update history

After testing, clean up the `test` stack:

```bash
pulumi stack select test
pulumi destroy
pulumi stack rm test
pulumi stack select dev
```

---

## Troubleshooting

### `pulumi: command not found`

Check the executable and `PATH`:

```bash
ls -la "$HOME/.pulumi/bin"
echo "$PATH"
command -v pulumi
```

Temporarily fix the current shell:

```bash
export PATH="$HOME/.pulumi/bin:$PATH"
```

Persist the setting:

```bash
echo 'export PATH="$HOME/.pulumi/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Cannot connect to the Docker daemon

Check the daemon:

```bash
sudo systemctl is-active docker
sudo systemctl status docker --no-pager
```

Start it when required:

```bash
sudo systemctl enable --now docker
```

### Permission denied on `/var/run/docker.sock`

Inspect permissions and group membership:

```bash
ls -l /var/run/docker.sock
id
```

Add the current user to the Docker group:

```bash
sudo usermod -aG docker "$USER"
newgrp docker
```

Then retest:

```bash
docker info
```

Do not use `sudo pulumi up` as the normal fix. It can create root-owned project, state, and plugin files.

### Port is already allocated

Identify listeners and containers using the port:

```bash
sudo ss -lntp | grep ':8080'
docker ps --format 'table {{.ID}}\t{{.Names}}\t{{.Ports}}'
```

Select another port:

```bash
pulumi config set hostPort 8081
pulumi preview
pulumi up
```

### Missing required configuration variable `webRoot`

Verify the active stack:

```bash
pulumi stack
```

Set the required value from the project root:

```bash
pulumi config set webRoot "$(pwd)/html"
pulumi config
```

### YAML parse error

Check indentation and avoid tabs:

```bash
sed -n '1,220p' Pulumi.yaml
```

Use an editor with YAML validation. Provider-property errors commonly include the exact invalid property path.

### Image pull failure

Test Docker independently:

```bash
docker pull nginx:alpine
```

Check DNS and HTTPS connectivity:

```bash
getent hosts registry-1.docker.io
curl -I https://registry-1.docker.io
```

In corporate networks, proxy settings may be required for both the interactive shell and Docker daemon.

### Provider plugin download failure

Inspect network connectivity and installed plugins:

```bash
pulumi plugin ls
curl -I https://api.pulumi.com
```

The exact endpoint used can vary. Check proxy, firewall, TLS interception, DNS, and outbound HTTPS rules.

### HTTP request fails after successful deployment

Check each layer separately:

```bash
pulumi stack output applicationUrl
docker ps --filter name=pulumi-nginx
docker logs pulumi-nginx
docker inspect pulumi-nginx --format '{{json .NetworkSettings.Ports}}'
sudo ss -lntp | grep ':8080\|:8081'
```

Also verify:

```bash
test -r html/index.html && echo OK
```

If running on a remote server, `localhost` refers to the server itself. Use the server IP or DNS name from the client, and confirm firewall rules permit access.

### Destroy cannot remove the image

An image can remain when another container, tag, or resource uses it. Inspect references:

```bash
docker ps -a --filter ancestor=nginx:alpine
docker image ls nginx
docker image inspect nginx:alpine
```

Do not force-remove an image on a shared host without checking consumers.

---

## Equivalent TypeScript and Python Resources

The project uses Pulumi YAML. The following examples demonstrate how the same basic image and container resources can be authored in other supported languages.

These language programs do not execute Docker commands directly. Their Pulumi SDK constructors register resources with the engine, and the Docker provider performs Docker API operations.

### TypeScript

```typescript
import * as docker from "@pulumi/docker";

const image = new docker.RemoteImage("nginxImage", {
  name: "nginx:alpine",
});

const container = new docker.Container("webContainer", {
  name: "pulumi-nginx",
  image: image.imageId,
  ports: [
    {
      internal: 80,
      external: 8080,
    },
  ],
});
```

TypeScript projects normally require Node.js and the relevant Pulumi packages.

### Python

```python
import pulumi_docker as docker

image = docker.RemoteImage(
    "nginxImage",
    name="nginx:alpine",
)

container = docker.Container(
    "webContainer",
    name="pulumi-nginx",
    image=image.image_id,
    ports=[
        {
            "internal": 80,
            "external": 8080,
        }
    ],
)
```

Python projects require Python and the relevant Pulumi packages.

### Pulumi YAML

```yaml
resources:
  nginxImage:
    type: docker:RemoteImage
    properties:
      name: nginx:alpine

  webContainer:
    type: docker:Container
    properties:
      name: pulumi-nginx
      image: ${nginxImage.imageId}
      ports:
        - internal: 80
          external: 8080
```

The differences are mainly in authoring syntax and the abstraction capabilities available in each language. The engine, state system, provider, and Docker API roles remain the same.

TypeScript or Python becomes especially useful when the infrastructure requires reusable functions, loops, tests, packages, custom component resources, or complex application logic.

---

## Security and Production Notes

This project is designed for learning. Before adapting it to production, consider the following.

### Docker socket access

Access to `/var/run/docker.sock` is highly privileged. Limit group membership and audit users who can access Docker.

### Network exposure

The example binds to `0.0.0.0`. This exposes the service on every IPv4 interface, subject to firewall rules. Use `127.0.0.1` when only local access is required.

### Image tags

Mutable tags such as `nginx:alpine` can point to different image content over time. Production systems should consider immutable digests and an explicit image promotion strategy.

### State backend

A local backend is not ideal for multi-user production environments. Use a shared backend with:

- Access controls
- Backups
- Encryption
- Concurrency handling
- Auditability
- Documented recovery procedures

### Secrets

Do not store plaintext credentials in `Pulumi.yaml`, shell history, or unencrypted repository files. Use Pulumi secrets and an appropriate secrets provider.

### Bind mounts

Bind mounts couple the container to a host path. For immutable and portable deployments, package content in a versioned image or use a controlled storage strategy.

### Backups

Back up stack state before risky state operations or backend migrations. Protect exported state files as potentially sensitive artifacts.

### Running Pulumi

Run Pulumi as the intended project user. Avoid mixing root and non-root execution because it can create ownership conflicts in project files, plugin directories, and local backend data.

---

## Recommended Repository Files

A clean repository can use this structure:

```text
pulumi-docker-yaml-lab/
├── .gitignore
├── README.md
├── Pulumi.yaml
├── Pulumi.dev.yaml
└── html/
    └── index.html
```

Recommended `.gitignore` entries:

```gitignore
# Exported Pulumi state backups
stack-backup.json
*.stack-backup.json

# Local editor and operating-system files
.vscode/
.idea/
.DS_Store

# Temporary files
*.tmp
*.log
```

`Pulumi.dev.yaml` is commonly committed when it contains environment configuration intended for the repository. Pulumi secret values are normally encrypted, but always review the file and your organization's policy before committing it.

Do not commit exported raw state backups to public source control.

---

## Command Reference

### Environment and network

```bash
cat /etc/os-release
uname -m
whoami
id
pwd
sudo -v
curl -I https://get.pulumi.com
curl -I https://download.docker.com
```

### Pulumi installation

```bash
curl -fsSL https://get.pulumi.com | sh
export PATH="$HOME/.pulumi/bin:$PATH"
echo 'export PATH="$HOME/.pulumi/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
command -v pulumi
pulumi version
```

### Docker verification

```bash
docker version
sudo systemctl is-active docker
docker info
docker run --rm hello-world
```

### Pulumi backend and project

```bash
pulumi login --local
pulumi whoami
mkdir -p ~/labs/pulumi-docker-yaml-lab
cd ~/labs/pulumi-docker-yaml-lab
pulumi new yaml --name pulumi-docker-yaml-lab --stack dev
```

### Configuration

```bash
pulumi config set webRoot "$(pwd)/html"
pulumi config set hostPort 8080
pulumi config
```

### Lifecycle

```bash
pulumi preview
pulumi up
pulumi stack
pulumi stack output
pulumi refresh
pulumi stack export > stack-backup.json
pulumi destroy
pulumi stack rm dev
```

### Validation

```bash
docker ps --filter name=pulumi-nginx
docker image ls nginx
docker network inspect pulumi-nginx-network
docker inspect pulumi-nginx
curl -fsS http://127.0.0.1:8080
```

---

## Official Documentation

- [Install Pulumi](https://www.pulumi.com/docs/install/)
- [Pulumi YAML](https://www.pulumi.com/docs/iac/languages-sdks/yaml/)
- [Pulumi YAML Language Reference](https://www.pulumi.com/docs/iac/languages-sdks/yaml/yaml-language-reference/)
- [Pulumi State and Backends](https://www.pulumi.com/docs/iac/concepts/state-and-backends/)
- [Pulumi Docker Provider](https://www.pulumi.com/registry/packages/docker/)
- [Docker Container Resource](https://www.pulumi.com/registry/packages/docker/api-docs/container/)
- [Docker RemoteImage Resource](https://www.pulumi.com/registry/packages/docker/api-docs/remoteimage/)
- [Docker Network Resource](https://www.pulumi.com/registry/packages/docker/api-docs/network/)
- [Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Docker Linux Post-Installation Steps](https://docs.docker.com/engine/install/linux-postinstall/)
