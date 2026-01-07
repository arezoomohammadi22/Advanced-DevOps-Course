# Exercise 01 – no-new-privileges (Blocking SetUID / SetGID Escalation)

> ⚠️ **Educational & Lab Use Only**
>
> This lab demonstrates how the Linux security flag **no-new-privileges (NNP)** completely prevents
> privilege escalation via **SetUID / SetGID binaries**, even when such binaries exist inside a container.

---

## 🎯 Goal of this exercise

You will prove that:

- A SetUID-root binary **can exist**
- The container user **can execute it**
- But **no privilege escalation happens**
- Because `no-new-privileges=true` blocks it at the kernel level

This is the **most important and effective single defense** against SetUID abuse in containers.

---

## 🔁 Prerequisite

You must have completed **Lab 00 (Baseline)** and already built the image:

```bash
docker build -t setuid-test .
```

The image must contain:
- `setuid.c`
- `/usr/local/bin/setuid-demo` (SetUID root)
- user `attacker`

---

## 🧠 What is no-new-privileges?

`no-new-privileges` is a Linux kernel security flag that says:

> A process and all its children are **never allowed to gain additional privileges**.

This means:
- SetUID binaries ❌
- SetGID binaries ❌
- File capabilities ❌
- Privilege-raising execve ❌

Once enabled, it **cannot be bypassed** from inside the container.

---

## 🧪 Step 1 – Run the container with no-new-privileges

From the host:

```bash
docker run --rm -it \
  --security-opt no-new-privileges:true \
  setuid-test
```

---

## 🧪 Step 2 – Verify current user

Inside the container:

```bash
id
```

Expected:

```text
uid=1000(attacker) gid=1000(attacker)
```

---

## 🧪 Step 3 – Execute the SetUID binary

```bash
/usr/local/bin/setuid-demo
```

---

## ❌ Expected result (IMPORTANT)

Instead of becoming root, you should see something similar to:

```text
setuid: Operation not permitted
```

Or:

- `[*] Before: uid=1000 euid=1000`
- UID remains `1000`

Confirm:

```bash
id
```

```text
uid=1000(attacker)
```

✔️ **Privilege escalation is fully blocked**

---

## 🧪 Step 4 – Inspect securebits (optional, recommended)

```bash
capsh --print
```

Look for this line:

```text
Securebits: ... (no-new-privs=1)
```

This confirms:
- The kernel is enforcing no-new-privileges
- SetUID is ignored even though the bit exists

---

## 🔬 Why this works (deep reason)

- Normally, SetUID changes **effective UID**
- With `no-new-privileges`, the kernel blocks **any exec that would increase privileges**
- The decision is made **before the program runs**
- The binary cannot override it, even as root

This is **not a Docker feature** – it is pure Linux kernel security.

---

## 🧠 Key takeaway

> **If you enable only ONE security option in Docker, make it no-new-privileges.**

It:
- Stops SetUID / SetGID attacks
- Stops file capability abuse
- Works even if the container is compromised

---

## ❌ Common mistakes

- Thinking `USER attacker` is enough ❌
- Relying only on `cap-drop` ❌
- Forgetting runtime flags ❌

---

## ✅ Recommended production baseline

```bash
docker run \
  --security-opt no-new-privileges:true \
  --cap-drop ALL \
  --read-only \
  --tmpfs /tmp \
  your-image
```

---

## 🔜 Next exercises

- **Exercise 02** – Capabilities + no-new-privileges
- **Exercise 03** – AppArmor profiles
- **Exercise 04** – SELinux policies
- **Exercise 05** – Docker User Namespace Remapping

---
