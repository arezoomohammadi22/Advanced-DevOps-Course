# Docker Privilege Escalation & Seccomp — Hands‑On Labs (DevSecOps)

This repository is a **hands‑on DevSecOps lab** that demonstrates **privilege escalation scenarios in Docker** and how **kernel‑level controls (seccomp, capabilities, namespaces)** change real outcomes.

Everything here is **tested, observable, and reproducible**.

> ⚠️ **Warning**: These labs are for **education on test systems only**. Never run them on production hosts.

---

## 1. Mental Model (Read This First)

Docker security is a set of **layers**, not a single control:

```
Application
  ↓
User / UID
  ↓
Linux Capabilities
  ↓
seccomp (syscall filter)
  ↓
AppArmor / SELinux
  ↓
Linux Kernel
```

**Privilege Escalation** happens when one of these layers is:
- Misconfigured
- Over‑permissive
- Disabled

---

## 2. Types of Privilege Escalation in Docker

### 2.1 Inside the Container

- Non‑root process becomes root **inside** container
- Usually caused by:
  - SUID binaries
  - Misconfigured services

> This alone is **not catastrophic**, unless combined with powerful capabilities.

---

### 2.2 Container → Host (Critical)

This is the real danger.

A container gains **host‑level control** via:
- Docker daemon
- Kernel interfaces
- Device access

---

## 3. LAB 1 — docker.sock = root on host

### Goal
Demonstrate why mounting Docker socket is equivalent to root access.

### Step 1 — Run a vulnerable container
```bash
docker run -it --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  alpine sh
```

### Step 2 — Install Docker CLI inside container
```bash
apk add --no-cache docker-cli
```

### Step 3 — Create a container with host filesystem
```bash
docker run --rm -it \
  -v /:/host \
  alpine sh
```

Inside the new container:
```bash
chroot /host sh
whoami
```

✅ **Result**: `root` on the host

### Security Lesson
- Docker daemon runs as root
- Access to docker.sock = full host compromise

---

## 4. LAB 2 — privileged container is not a container

### Goal
Show that `--privileged` removes isolation.

```bash
docker run --rm -it --privileged alpine sh
```

Inside container:
```bash
mount | head
ls /dev
```

Optional (dangerous test):
```bash
mount /dev/sda1 /mnt
```

### Security Lesson
- privileged ≈ host process
- Avoid in almost all cases

---

## 5. LAB 3 — CAP_SYS_ADMIN (the most dangerous capability)

### Goal
Demonstrate that one capability can enable powerful actions.

```bash
docker run --rm -it \
  --cap-add SYS_ADMIN \
  alpine sh
```

Inside container:
```bash
mount -t tmpfs tmpfs /mnt
df -h | grep /mnt
```

### Security Lesson
- CAP_SYS_ADMIN is effectively "half‑privileged"
- Must be avoided unless absolutely required

---

## 6. LAB 4 — seccomp blocks privilege escalation

### Goal
Show that seccomp blocks dangerous syscalls even with capabilities.

### seccomp profile (modern Linux mount API)
```json
{
  "defaultAction": "SCMP_ACT_ALLOW",
  "syscalls": [
    { "names": ["move_mount"], "action": "SCMP_ACT_ERRNO", "errnoRet": 1 }
  ]
}
```

### Run container
```bash
docker run --rm -it \
  --cap-add SYS_ADMIN \
  --security-opt seccomp=./seccomp-profile.json \
  alpine sh
```

Inside container:
```bash
mount -t tmpfs tmpfs /mnt
```

❌ Mount fails

### Security Lesson
- seccomp filters syscalls, not commands
- seccomp executes **after capability checks**

---

## 7. LAB 5 — Why blocking `mount()` alone does not work

### Explanation
On modern kernels, `mount` does **not** call the legacy `mount()` syscall.

It uses the **new mount API**:
- fsopen
- fsconfig
- fsmount
- move_mount

### Proof
```bash
strace -f -e trace=mount,fsopen,fsconfig,fsmount,move_mount \
  mount -t tmpfs tmpfs /mnt
```

### Security Lesson
- Legacy seccomp profiles are ineffective on modern Linux
- Always confirm syscall behavior with `strace`

---

## 8. LAB 6 — no‑new‑privileges (last line of defense)

### Goal
Prevent privilege gain even if exploit exists.

```bash
docker run --rm -it \
  --security-opt no-new-privileges:true \
  alpine sh
```

### Security Lesson
- Blocks privilege escalation via SUID / file capabilities
- Highly recommended for production

---

## 9. How to Prove What Actually Happened

### A) Check mount result
```bash
df -h | grep /mnt
```

### B) Check exit code
```bash
echo $?
```

### C) Kernel logs (host)
```bash
dmesg | tail -n 50
```

---

## 10. Production Hardening Checklist

✅ Run containers as non‑root
✅ Drop all capabilities by default
✅ Avoid CAP_SYS_ADMIN
✅ Never mount docker.sock
✅ Use seccomp RuntimeDefault or custom
✅ Enable AppArmor / SELinux
✅ Use no‑new‑privileges

---

## 11. Key Takeaways

- Docker isolation is **configuration‑dependent**
- One misconfiguration can break all guarantees
- seccomp is one of the strongest kernel defenses
- Privilege escalation is usually a chain, not a single bug

---

**End of README**

