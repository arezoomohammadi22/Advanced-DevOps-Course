# Abusing SetUID / SetGID Binaries in Docker (DevSecOps Lab)

> ⚠️ **Educational & Lab Use Only**
>
> This lab is designed strictly for security education, DevSecOps training, and understanding privilege escalation mechanics inside Docker containers. **Do NOT use this knowledge to attack real systems.**

---

## 🎯 Lab Objectives

In this lab you will learn:

- What SetUID / SetGID binaries are and how they work
- The difference between **UID** and **Effective UID (EUID)**
- How SetUID binaries can be abused inside Docker containers
- How privilege escalation happens **inside a container**
- Why container root ≠ host root (but still dangerous)
- Practical **defensive techniques** to prevent this class of attacks

---

## 🧠 Prerequisites

- Basic Linux knowledge
- Docker installed
- Understanding of users, UID, GID
- Intro-level security concepts

---

## 🔍 Background: SetUID / SetGID Explained

- **SetUID (Set User ID)**: When a binary has the SetUID bit enabled, it runs with the **effective UID of the file owner**, not the user who executed it.
- **SetGID (Set Group ID)**: Same concept, but for group privileges.

This mechanism exists for legitimate reasons (e.g., `passwd`), but it becomes dangerous in containers when misused.

---

## 🧪 Attack Scenario Overview

We will:

1. Create a simple C program that calls `setuid(0)`
2. Compile it inside a Docker image
3. Mark the binary as **SetUID root**
4. Run the container as a non-root user (`attacker`)
5. Execute the binary and gain **root privileges inside the container**

---

## 🧾 Step 1: Vulnerable C Program (SetUID Abuse)

### `setuid.c`

```c
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>

int main() {
    printf("[*] Before: uid=%d euid=%d\n", getuid(), geteuid());

    if (setuid(0) != 0) {
        perror("setuid");
        return 1;
    }

    printf("[*] After : uid=%d euid=%d\n", getuid(), geteuid());
    execl("/bin/sh", "sh", "-p", NULL);
    perror("execl");
    return 1;
}
```

---

## 🐳 Step 2: Dockerfile (Vulnerable Image)

```dockerfile
FROM debian:12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc6-dev passwd \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash attacker

WORKDIR /opt
COPY setuid.c /opt/setuid.c

RUN gcc /opt/setuid.c -o /usr/local/bin/setuid-demo

RUN chown root:root /usr/local/bin/setuid-demo \
 && chmod 4755 /usr/local/bin/setuid-demo

USER attacker
CMD ["/bin/bash"]
```

---

## 🏗️ Step 3: Build & Run

```bash
docker build -t setuid-test .
docker run --rm -it setuid-test
```

Inside the container:

```bash
id
/usr/local/bin/setuid-demo
id
```

### Expected Output

```
uid=1000(attacker)
[*] Before: uid=1000 euid=0
[*] After : uid=0 euid=0
```

---

## 🔎 Inspecting the Binary: Why is `euid=0`?

Before jumping to defenses, it is important to **visually verify** why the binary runs with `euid=0`.

Inside the container, run:

```bash
ls -l /usr/local/bin/setuid-demo
stat /usr/local/bin/setuid-demo | egrep "Uid|Gid|Access"
```

### Expected Output Explanation

- In the `ls -l` output, you should see something like:

```text
-rwsr-xr-x 1 root root 16712 setuid-demo
```

- The **`s`** in `-rwsr-xr-x` indicates the **SetUID bit** is enabled.
- The file owner is **root**, which means:
  - The binary executes with **Effective UID = root**
  - Even when executed by a non-root user (`attacker`)

- The `stat` output confirms:
  - File ownership (`Uid: ( 0/ root )`)
  - Permission bits (`Access: (4755/-rwsr-xr-x)`)

📌 This is the direct reason why `geteuid()` returns `0` **before** calling `setuid(0)` in the program.

---

## 🛡️ Defense Techniques

### no-new-privileges

```bash
docker run --rm -it \
  --security-opt no-new-privileges:true \
  setuid-test
```

### Drop Capabilities

```bash
docker run --rm -it \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  setuid-test
```

### nosuid Mount

```bash
docker run --rm -it \
  --tmpfs /mnt:rw,nosuid,nodev,noexec \
  setuid-test
```

---

## 🧠 Key Takeaways

- SetUID executes with owner privileges
- Inside Docker, this enables container-level root escalation
- `no-new-privileges` is the strongest immediate mitigation
- Always apply defense-in-depth

---


