# Baseline: Abusing a SetUID Binary in Docker (Lab 0)

> ⚠️ **Educational & Lab Use Only**
>
> This content is for DevSecOps/security training to understand how **SetUID/SetGID binaries** can lead to **privilege escalation inside a container**, and how to mitigate it safely. Do not use this on real systems you do not own/operate.

---

## What you will build (baseline)

You will build a Docker image that contains:

- A minimal C program that tries to switch to `UID 0` (root) using `setuid(0)`
- A non-root user named `attacker`
- A compiled binary owned by `root` with the **SetUID bit** enabled (`chmod 4755`)

When `attacker` runs the binary:

- The binary starts with **EUID=0** due to SetUID (even though `attacker` is not root)
- It then attempts to make the **real UID** become 0 (root) via `setuid(0)`
- Finally it spawns a shell

This is a classic **container-level privilege escalation** demo.

---

## Why this matters

- **Root inside a container is not automatically root on the host.** Namespaces isolate a lot.
- But **container root is still dangerous**, and misconfigurations (e.g., `--privileged`, mounting `/var/run/docker.sock`, excessive capabilities, weak LSM policies) can turn container-root into **host compromise**.

This baseline lab is the foundation for the mitigations labs:
- `no-new-privileges`
- capabilities hardening
- AppArmor / SELinux policies
- user namespace remapping

---

## Files in this lab

- `setuid.c` — the vulnerable demo program
- `Dockerfile` — builds the image, creates `attacker`, compiles, and sets SetUID  
  - Includes `libcap2-bin` so you can use `capsh` for capability inspection.

---

## Step 1 — Review the C program

Open `setuid.c`:

- `getuid()` returns the **real UID** (who you are)
- `geteuid()` returns the **effective UID** (what privileges the process is running with)
- With a SetUID-root binary, `geteuid()` becomes 0 even if `getuid()` is 1000

---

## Step 2 — Build the Docker image

From this directory:

```bash
docker build -t setuid-test .
```

---

## Step 3 — Run the baseline (vulnerable) container

```bash
docker run --rm -it setuid-test
```

Inside the container, verify you are `attacker`:

```bash
id
```

Expected (similar):

```text
uid=1000(attacker) gid=1000(attacker) groups=1000(attacker)
```

---

## Step 4 — Confirm SetUID on the binary (why EUID becomes 0)

Inside the container:

```bash
ls -l /usr/local/bin/setuid-demo
stat /usr/local/bin/setuid-demo | egrep "Uid|Gid|Access"
```

Expected highlights:

- `ls -l` shows `-rwsr-xr-x` (note the **s**)
- The owner is `root:root`
- `stat` shows `Access: (4755/-rwsr-xr-x)` and `Uid: ( 0/ root )`

That **SetUID bit** (`4755`) is the direct reason `geteuid()` returns 0.

---

## Step 5 — Execute the binary (observe privilege escalation)

Still inside the container:

```bash
/usr/local/bin/setuid-demo
```

Expected output (similar):

```text
[*] Before: uid=1000 euid=0
[*] After : uid=0 euid=0
```

Now you are in a root shell inside the container. Confirm:

```bash
id
```

---

## Step 6 — Capability inspection (optional but recommended)

Because the Dockerfile installs `libcap2-bin`, you can inspect capabilities:

```bash
capsh --print
```

This is useful later when you run with `--cap-drop ALL` and compare output.

---

## Common pitfalls / troubleshooting

### 1) “SetUID doesn't work”
Common reasons:

- The binary is not owned by `root`
- The SetUID bit is not set (`chmod 4755 ...`)
- The filesystem mount has `nosuid`
- Runtime uses `--security-opt no-new-privileges:true` (it blocks gaining privileges via SetUID/SetGID)

### 2) “I get EUID=0 but UID doesn't become 0”
This can happen depending on runtime hardening (capabilities dropped, LSM policy, or securebits).
In later labs you will intentionally cause this behavior to demonstrate defenses.

---

