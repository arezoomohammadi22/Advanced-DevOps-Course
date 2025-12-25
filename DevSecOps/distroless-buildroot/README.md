# Secure Distroless Docker Image using Buildroot (ARM64)

This repository documents **step-by-step how to download, configure, build, and use Buildroot** to create a **minimal (distroless) Linux root filesystem**, and then convert it into a **Docker image built FROM scratch**.

This work follows the instructor’s explanations in the DevSecOps course and focuses on **security, reproducibility, and full control over the supply chain**.

---

## 🎯 What We Are Building

- A **custom Linux Root Filesystem (rootfs)** using **Buildroot**
- Target architecture: **ARM64 (AArch64)**
- libc: **musl** (smaller & safer)
- Userspace: **BusyBox**
- Output: `rootfs.tar`
- Final artifact: **Distroless Docker Image (FROM scratch)**

No Ubuntu, no Alpine, no package manager in runtime.

---

## 🧠 High-Level Flow (Instructor’s Architecture)

```
Clone Buildroot
      ↓
menuconfig (select arch, libc, rootfs type)
      ↓
Build custom toolchain + rootfs
      ↓
output/images/rootfs.tar
      ↓
Dockerfile (FROM scratch)
      ↓
Golden Distroless Image
```

---

## 🧰 Host Prerequisites

On your **ARM64 host** (or ARM64 VM):

```bash
sudo apt update
sudo apt install -y \
  build-essential \
  libncurses-dev \
  flex \
  bison \
  wget \
  curl \
  rsync \
  bc \
  file \
  python3
```

Docker must also be installed.

---

## 📥 Step 1: Download Buildroot (Git)

Clone the official Buildroot repository:

```bash
git clone https://github.com/buildroot/buildroot.git
cd buildroot
```

(Optional) Checkout a stable release:

```bash
git checkout 2024.02
```

---

## ⚙️ Step 2: Run menuconfig

Before running menuconfig, make sure your terminal is large enough:

```bash
export COLUMNS=120
export LINES=40
```

Run configuration:

```bash
make menuconfig
```

---

## 🧩 Step 3: Required menuconfig Changes

### 🎯 Target Architecture

```
Target options  --->
  Target Architecture (AArch64 (little endian))
```

---

### 🧰 Toolchain Configuration

```
Toolchain  --->
  Toolchain type (Buildroot toolchain)
  C library (musl)
```

Why:
- Smaller binaries
- Reduced attack surface
- Ideal for containers

---

### 📦 Target Packages (Userspace)

```
Target packages  --->
  BusyBox  --->
    [*] busybox
```

Do **NOT** enable extra packages unless required.

---

### 🗂️ Filesystem Image Output (CRITICAL)

```
Filesystem images  --->
  [*] tar the root filesystem
```

This is mandatory for Docker.

---

### ❌ Kernel Build (Disable)

```
Kernel  --->
  [ ] Linux Kernel
```

Reason:
- Containers use the **host kernel**

---

## 🏗️ Step 4: Build Root Filesystem

Start the build:

```bash
make -j$(nproc)
```

Buildroot will:
- Build its **own toolchain**
- Build BusyBox
- Assemble a minimal root filesystem

Final output:

```
output/images/rootfs.tar
```

---

## 📦 What is rootfs.tar?

- A complete Linux filesystem
- No package manager
- No compiler
- Minimal binaries
- Owned as root (fakeroot)

This is exactly what the instructor described.

---

## 🐳 Step 5: Create Dockerfile (FROM scratch)

Create a `Dockerfile` next to `rootfs.tar`:

```dockerfile
FROM scratch
ADD rootfs.tar /
CMD ["/bin/sh"]
```

---

## 🐋 Step 6: Build Docker Image

```bash
docker build -t buildroot-distroless:arm64 .
```

---

## ▶️ Step 7: Run Container

```bash
docker run -it --rm buildroot-distroless:arm64
```

You should land inside a **minimal BusyBox shell**.

---

## 🔐 Security Properties (Why This Matters)

- No package manager
- No shell utilities beyond BusyBox
- musl libc instead of glibc
- Very small attack surface
- Perfect for:
  - Golden images
  - Secure CI/CD
  - Production containers

Example hardened run:

```bash
docker run \
  --read-only \
  --cap-drop=ALL \
  --security-opt no-new-privileges \
  buildroot-distroless:arm64
```

---

## 🏆 Golden Image Usage

Use this image as a base:

```dockerfile
FROM buildroot-distroless:arm64
COPY myapp /usr/bin/myapp
CMD ["/usr/bin/myapp"]
```

Your application should be:
- Precompiled
- Preferably static
- Built with the same Buildroot toolchain

---

## ❓ Why Not Alpine or Ubuntu?

| Feature | Alpine | Ubuntu | Buildroot Distroless |
|------|--------|--------|----------------------|
| Package manager | Yes | Yes | ❌ No |
| Attack surface | Medium | High | **Minimal** |
| Supply-chain control | Low | Low | **Full** |
| Reproducibility | Medium | Medium | **High** |

---

## 📚 References

- https://buildroot.org
- https://musl.libc.org
- https://busybox.net

---



