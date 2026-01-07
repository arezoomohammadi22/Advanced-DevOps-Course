# DeepCE Lab (Host) — Install, Run, and Interpret Output

This README is designed for a **safe, hands-on lab** where you run **DeepCE** on a Linux **host** to enumerate Docker exposure (especially `docker.sock`).

> **What DeepCE is:** DeepCE (Docker Enumeration, Escalation of Privileges and Container Escapes) is a shell script that audits a machine/container for Docker-related misconfigurations and common escalation paths.  
> **Use it for:** Defensive auditing, blue-team validation, and controlled training labs.

---

## 0) Safety & Scope

✅ Recommended lab environment:
- A dedicated VM (Ubuntu 22.04 LTS is fine)
- Docker installed
- Non-production system

⚠️ Do **NOT** run this on systems you don’t own or don’t have explicit permission to test.

---

## 1) Prerequisites

Check Docker is installed and reachable:

```bash
docker --version
docker info >/dev/null && echo "Docker OK" || echo "Docker not reachable"
```

If Docker isn't installed (Ubuntu):
```bash
sudo apt update
sudo apt install -y docker.io git
sudo systemctl enable --now docker
```

---

## 2) Install DeepCE

### Option A — via Git (recommended)
```bash
mkdir -p ~/devsec && cd ~/devsec
git clone https://github.com/stealthcopter/deepce.git
cd deepce
chmod +x deepce.sh
```

### Quick check
```bash
./deepce.sh -h || ./deepce.sh help || true
```

---

## 3) Run DeepCE on the Host

### Basic run (no auto-install of dependencies)
```bash
sudo ./deepce.sh
```

### Run with dependency auto-install
DeepCE can attempt to detect missing tools and install them:
```bash
sudo ./deepce.sh install
```

> **Tip:** If your host has no internet access, use the basic run, or pre-install dependencies manually (e.g., `curl`, `iproute2`, `net-tools`, `nmap`).

---

## 4) Understanding the Output (What It Means)

DeepCE output is grouped into sections like:
- **Enumerating Platform**
- **Enumerating Containers**
- **Network / DNS / Kernel / Capabilities**
- **Misconfigurations & Exploitability checks**

Below are the most important lines you will commonly see **when running on the host**.

---

### 4.1 Inside Container

Example:
```
[+] Inside Container ........ No
```

**Meaning:** DeepCE detected you are running **on the host**, not inside a container.  
If it says **Yes**, you are inside a container and checks will focus on escape paths.

---

### 4.2 User / Groups / Sudoers

Example:
```
[+] User .................... root
[+] Sudoers ................. Yes
```

**Meaning:**  
- If `User` is `root`, you already have full privileges on the host.
- If the user is not root but is in **sudoers**, they can escalate to root (depending on policy).

> In training labs, you often run DeepCE as `sudo` to see all checks.  
> For real audits, run as the *least-privileged* user first, then compare.

---

### 4.3 Docker Executable & Version

Example:
```
[+] Docker Executable ....... /usr/bin/docker
[+] Docker version .......... 28.2.2
```

**Meaning:** Docker is installed; DeepCE can query local Docker.

---

### 4.4 Rootless (Important!)

Example:
```
[+] Rootless ................ No
```

**Meaning:** Docker is running in **rootful mode** (dockerd runs with root privileges).  
This is normal on many systems.

✅ Rootless Docker is different from `userns-remap`.  
- `userns-remap` remaps container UIDs to unprivileged host UIDs.
- **Rootless Docker** runs the Docker daemon *without root*.

---

### 4.5 Docker Socket Found (Critical)

Example:
```
[+] Docker Sock ............. Yes
srw-rw---- 1 root docker 0 Jan  1 12:56 /var/run/docker.sock
[+] Sock is writable ........ Yes
```

**Meaning:**  
- The file `/var/run/docker.sock` is the local Docker API endpoint (Unix socket).
- If it’s writable by your current user, you can issue Docker API calls.  
  In most environments, **writable docker.sock = effective root on the host**.

Why? Because a user who can talk to the Docker daemon can create privileged containers or mount the host filesystem.

DeepCE often suggests:
```bash
curl -s --unix-socket /var/run/docker.sock http://localhost/info
```

This prints Docker daemon metadata (`KernelVersion`, `OperatingSystem`, etc.).

---

### 4.6 CVE Checks

Example:
```
[+] CVE–2019–13139 .......... No
[+] CVE–2019–5736 ........... No
```

**Meaning:** DeepCE tested for known older vulnerabilities; `No` indicates those specific CVEs are not detected as exploitable.

✅ Important: Even if CVEs are **No**, a **writable docker.sock** can still be enough to compromise the host (misconfiguration vs. vulnerability).

---

### 4.7 Enumerating Containers

Example:
```
[+] Docker Containers........ 2 Running, 2 Total
CONTAINER ID   IMAGE         COMMAND       STATUS              NAMES
...
```

**Meaning:** DeepCE can list containers. If you can list containers via the socket, you can usually:
- start/stop containers
- exec commands in containers
- create new containers

---

## 5) Quick Verification Commands (Host)

### Confirm socket permissions
```bash
ls -l /var/run/docker.sock
```

### Confirm who can access it
```bash
id
getent group docker
```

### Query Docker daemon info via socket
```bash
sudo curl -s --unix-socket /var/run/docker.sock http://localhost/info | head
```

---

## 6) Defensive Notes (What to Fix)

If DeepCE reports **`Sock is writable: Yes`** for an untrusted user or inside a container, common mitigations include:

- **Do not mount** `/var/run/docker.sock` into containers unless strictly required.
- Restrict access to the `docker` group; treat it like `root`.
- Prefer **rootless Docker** where feasible (reduces blast radius).
- Use `userns-remap` *and* other hardening (AppArmor/SELinux, drop capabilities).
- Avoid exposing Docker over TCP without TLS (e.g., `0.0.0.0:2375`).

---

## 7) Troubleshooting

### “Permission denied” on docker commands
- You’re not root and not in the `docker` group:
```bash
sudo usermod -aG docker $USER
newgrp docker
```
Then retry: `docker ps`

### DeepCE can’t install packages
- Your host may not have internet access, or `apt/yum` is blocked.
- Run without `install` and install tools manually.

---

## 8) Suggested Lab Flow (What to Practice)

1. Run `sudo ./deepce.sh` on the host.
2. Identify:
   - Is Docker rootless?
   - Is docker.sock present?
   - Is it writable?
3. Run `curl --unix-socket ... /info` and match fields to DeepCE output.
4. List containers and reason about the risk.
5. Write a “Findings” note:
   - *Finding:* Writable docker.sock
   - *Impact:* Effective root via Docker API
   - *Fix:* Restrict group access / remove socket mount / rootless Docker, etc.

---

## References
- DeepCE docs site: https://stealthcopter.github.io/deepce
- DeepCE repository: https://github.com/stealthcopter/deepce
