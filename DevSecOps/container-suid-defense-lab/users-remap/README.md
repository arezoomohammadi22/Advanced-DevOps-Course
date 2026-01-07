# Exercise 05 – Docker User Namespace Remapping (userns-remap)

> ⚠️ **Educational & Lab Use Only**
>
> This lab explains and demonstrates **Docker User Namespace Remapping** and why it is one of the
> most important **host-protection mechanisms** in container security.
>
> User namespace remapping does **NOT** prevent container compromise.
> It prevents a compromised container from becoming a **host compromise**.

---

## 🎯 Goal of this exercise

By completing this lab, you will understand and **prove in practice** that:

- `root` inside a container is **not necessarily** `root` on the host
- Docker normally maps container UIDs **1:1** to host UIDs
- With **userns-remap**, container `UID 0` maps to an **unprivileged host UID**
- Even if an attacker becomes `root` inside the container, the **host remains protected**

---

## 🧠 The core problem (default Docker behavior)

By default, Docker does **not** enable user namespaces.

This means UID mapping looks like this:

```
Container UID 0     → Host UID 0
Container UID 1000  → Host UID 1000
```

### Why this is dangerous

If a container is misconfigured or compromised:
- SetUID abuse
- Excessive Linux capabilities
- Mounted Docker socket
- Kernel vulnerabilities

Then:

> **Container root can become host root**

---

## ✅ What User Namespace Remapping does

User namespace remapping changes UID/GID mapping:

```
Container UID 0      → Host UID 493216
Container UID 1      → Host UID 493217
Container UID 1000   → Host UID 494216
```

So:

- Inside container: attacker sees `uid=0 (root)`
- On the host: the same process runs as an **unprivileged UID**
- Host kernel enforces the mapping

This breaks the direct trust relationship between container root and host root.

---

## 🧱 Mental security model

### Without userns-remap

```
[ container root (UID 0) ] ───▶ [ host root (UID 0) ] ❌
```

### With userns-remap

```
[ container root (UID 0) ] ───▶ [ host UID 493216 ] ✅
```

---

## 🛠️ Implementation (Host-level configuration)

⚠️ **This configuration is done on the Docker host, not inside the container.**

---

### Step 1 – Create a dedicated remap user and group

Run on the **host**:

```bash
groupadd dockremap
useradd -g dockremap dockremap
```

This user:
- Is not used for login
- Exists only for UID/GID mapping
- Has no special privileges

---

### Step 2 – Configure Docker daemon

Edit the Docker daemon configuration file:

```bash
/etc/docker/daemon.json
```

Add:

```json
{
  "userns-remap": "dockremap"
}
```

This tells Docker:

> Map container UIDs/GIDs to the `dockremap` user namespace.

---

### Step 3 – Restart Docker

```bash
systemctl restart docker
```

⚠️ Important notes:
- All running containers will stop
- Docker will create new storage paths such as:

```
/var/lib/docker/493216.493216/
```

The presence of this directory confirms that **user namespace remapping is active**.

---

## 🧪 Verification (critical part)

### Step 4 – Run the container (non-root)

```bash
docker run --rm -it setuid-test
```

Inside the container:

```bash
id
```

Expected:

```text
uid=1000(attacker) gid=1000(attacker)
```

This is expected because the Dockerfile uses:

```
USER attacker
```

---

### Step 5 – Trigger privilege escalation inside container

Inside the container:

```bash
/usr/local/bin/setuid-demo
id
sleep 300
```

Expected:

```text
[*] Before: uid=1000 euid=0
[*] After : uid=0 euid=0
```

The attacker becomes **root inside the container**.

---

### Step 6 – Verify host-side UID mapping

On the **host**, find the process:

```bash
ps -eo pid,user,cmd | grep "sleep 300"
```

Example output:

```text
702508  494216  sleep 300
```

Now inspect `/proc`:

```bash
cat /proc/702508/status | egrep "Uid|Gid"
```

Expected:

```text
Uid:    494216  494216  494216  494216
Gid:    494216  494216  494216  494216
```

📌 **This is the proof:**

> Container root (UID 0) is mapped to an unprivileged host UID (494216)

---

## 🔬 Security impact analysis

### What userns-remap protects against

| Threat | Result |
|------|------|
| SetUID escalation inside container | ❌ Not prevented |
| Container root → host root | ✅ Prevented |
| Simple container escapes | ✅ Much harder |
| Accidental host file overwrite | ✅ Reduced impact |

### What it does NOT protect against

- Kernel vulnerabilities
- Malicious mounts of `/var/run/docker.sock`
- Privileged containers (`--privileged`)

---

## ⚠️ Trade-offs and limitations

### 1️⃣ Volume and bind-mount permissions

Because UIDs are remapped:
- Some volumes may fail with `permission denied`
- You may need to:
  - `chown` directories to remapped UID ranges
  - Adjust ACLs

---

### 2️⃣ Image compatibility issues

Some images:
- Assume real root access
- Hardcode UID expectations

These images may break under userns-remap.

---

### 3️⃣ Docker socket remains dangerous

Even with userns-remap:

```bash
-v /var/run/docker.sock:/var/run/docker.sock
```

❌ **Still extremely dangerous**

---

## 🏆 Position in Defense-in-Depth

Recommended security layering:

1. `no-new-privileges` → blocks privilege escalation
2. `cap-drop ALL` → limits root power
3. AppArmor / SELinux → enforces behavior
4. **userns-remap** → protects the host

> User namespace remapping is the **last line of defense**.

---

## 🧠 Key takeaway

> **User namespace remapping does not stop attackers from becoming root inside a container.  
> It stops them from becoming root on the host.**

---
