# DeepCE in Docker Containers — Installation, Execution, and Security Analysis

This README explains **how to run DeepCE inside a Docker container**, how to **interpret its output**, how **Docker socket mounting enables access to the Docker daemon via curl**, why this is **dangerous**, and how **user namespace remapping (userns-remap)** changes the results.

This document is suitable for **GitHub**, **training labs**, and **security demonstrations**.

---

## ⚠️ Disclaimer

This content is for **educational and defensive security purposes only**.

- Run these labs **only on systems you own or are authorized to test**
- Use a **local VM or lab environment**
- Never expose Docker sockets in production

---

## 1. What Is DeepCE?

**DeepCE** stands for:

> **Docker Enumeration, Escalation of Privileges, and Container Escapes**

It is a **bash-based security auditing tool** that:
- Detects whether it is running on a **host or inside a container**
- Enumerates **Docker misconfigurations**
- Identifies **privilege escalation and container escape paths**
- Helps **validate defensive hardening**

DeepCE is primarily an **enumeration and validation tool**, not a fully automated exploit framework.

---

## 2. Running DeepCE Inside a Docker Container (Baseline)

### 2.1 Start a Normal (Safer) Container

```bash
docker run -it --rm ubuntu:22.04 bash
```

Install dependencies and DeepCE:

```bash
apt update
apt install -y git curl procps iproute2 libcap2-bin
git clone https://github.com/stealthcopter/deepce.git
cd deepce
chmod +x deepce.sh
./deepce.sh
```

### Expected Results

Typical output highlights:
- `Inside Container: Yes`
- `Docker Sock: Not Found`
- Limited capabilities
- No direct Docker daemon access

**Meaning:**  
This container is reasonably isolated. No Docker escape via socket is possible.

---

## 3. Running DeepCE with Docker Socket Mounted (Dangerous)

### 3.1 Start Container with docker.sock Mounted

```bash
docker run -it --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  ubuntu:22.04 bash
```

Install tools and DeepCE again:

```bash
apt update
apt install -y git curl procps iproute2 libcap2-bin
git clone https://github.com/stealthcopter/deepce.git
cd deepce
chmod +x deepce.sh
./deepce.sh
```

---

## 4. Understanding Critical DeepCE Output

### 4.1 Docker Socket Detection

Example:
```
Docker Sock ............. Yes
Sock is writable ........ Yes
```

**Meaning:**  
The container can communicate with the **Docker daemon on the host**.

This is **equivalent to root-level access** on the host.

---

### 4.2 Why docker.sock Is Dangerous

The Docker socket is the **Docker API endpoint**.

If writable, an attacker can:
- Create new containers
- Run privileged containers
- Mount the host filesystem
- Read sensitive files (`/etc/shadow`)
- Achieve full host compromise

> **Writable docker.sock = root on the host**

---

## 5. Accessing Docker Daemon via curl (Proof of Control)

Even without Docker CLI, you can talk directly to Docker using `curl`.

### 5.1 Test Connectivity

```bash
curl --unix-socket /var/run/docker.sock http://localhost/_ping
```

Expected output:
```
OK
```

This confirms **direct access to the Docker daemon**.

---

### 5.2 Query Docker Daemon Info

```bash
curl --unix-socket /var/run/docker.sock http://localhost/info | head
```

This returns:
- Host kernel version
- OS details
- Docker root directory
- Number of CPUs

---

### 5.3 Creating a Container via Docker API (Conceptual)

With full socket access, an attacker can use the Docker API to:
- Create containers
- Start them
- Attach shells

This can be done **without the docker CLI**, purely via HTTP calls.

---

## 6. Why This Leads to Host Compromise

Once the daemon is accessible, the attacker can instruct Docker to run:

- A **privileged container**
- A container with `/` mounted from the host
- A container that executes arbitrary commands

At this point:
> Container isolation is completely broken.

---

## 7. DeepCE Output with userns-remap Enabled

If Docker is configured with:

```json
"userns-remap": "default"
```

or a custom remap user (e.g., `dockremap`), DeepCE output often changes:

Example:
```
Docker Sock ............. Yes
Sock is writable ........ No
```

or ownership appears as:
```
nobody:nogroup
```

### Meaning

- Docker socket may be mounted
- **UID/GID remapping prevents effective access**
- Docker API calls fail due to permission mismatch

This indicates **partial mitigation**.

---

## 8. Important Clarification: userns-remap vs Rootless Docker

| Feature | userns-remap | Rootless Docker |
|------|-------------|----------------|
Docker daemon runs as root | Yes | No |
UID remapping | Yes | Yes |
docker.sock risk | Reduced | Strongly reduced |
DeepCE "Rootless" check | No | Yes |

> userns-remap hardens containers  
> **Rootless Docker hardens the daemon itself**

---

## 9. Interpreting Your Results (Quick Guide)

Ask these questions after running DeepCE:

1. Am I inside a container or on the host?
2. Is docker.sock present?
3. Is it writable?
4. Can I access Docker API via curl?
5. Are results different with userns-remap enabled?

---

## 10. Defensive Recommendations

- ❌ Never mount `/var/run/docker.sock` into containers
- ❌ Never expose Docker TCP (`0.0.0.0:2375`) without TLS
- ✅ Use `userns-remap`
- ✅ Prefer **Rootless Docker**
- ✅ Use AppArmor / SELinux
- ✅ Drop unnecessary Linux capabilities

---

## 11. Key Takeaway

> **DeepCE does not “hack” Docker — it proves when Docker is already misconfigured.**

If DeepCE reports Docker socket access, the system is **inherently insecure by design**.

---
