# Secure Distroless Docker Image using Buildroot (ARM64)

This repository demonstrates how to build a **minimal, secure, and reproducible distroless Docker image** from scratch using **Buildroot**, following **DevSecOps best practices**.

The goal is to avoid using pre-built base images (Alpine, Ubuntu, Debian) and instead generate a **custom Linux root filesystem**, then convert it into a hardened Docker image.

---

## 🎯 Project Goals

- Build a **custom Linux root filesystem** using Buildroot
- Use **musl libc** for reduced attack surface
- Avoid package managers in runtime images
- Create a **distroless Docker image**
- Enable **Golden Image** strategy for CI/CD
- Support **ARM64 (AArch64)** architecture
- Prepare a base for container hardening (capabilities, seccomp, read-only FS)

---

## 🧠 Architecture Overview

```
+---------------------------+
|        Application        |
|   (static / minimal)      |
+---------------------------+
|        RootFS             |
|  (BusyBox + musl libc)    |
+---------------------------+
|        Kernel             |
|  (Host Kernel / Runtime)  |
+---------------------------+
|        Hardware           |
+---------------------------+
```

- No shell tools except BusyBox
- No package manager
- No build tools inside the container
- Uses host kernel (container model)

---

## 🧰 Prerequisites

Host system requirements:

```bash
sudo apt install -y \
  build-essential \
  libncurses-dev \
  flex \
  bison \
  wget \
  curl \
  rsync \
  python3 \
  bc \
  file
```

Docker must be installed on the host.

---

## 🏗️ Buildroot Configuration Summary

Key Buildroot settings:

- **Target Architecture:** `AArch64 (ARM64)`
- **C Library:** `musl`
- **Init system:** BusyBox
- **Filesystem output:** `rootfs.tar`
- **Package manager:** ❌ Disabled
- **Kernel build:** ❌ Not included (container uses host kernel)

Configuration is done via:

```bash
make menuconfig
```

Important options:

```
Target options  --->
  Target Architecture = AArch64

Toolchain  --->
  C library = musl

Filesystem images  --->
  [*] tar the root filesystem

Target packages  --->
  BusyBox  --->
    [*] Enable
```

---

## ⚙️ Build Root Filesystem

Run the full Buildroot build:

```bash
make -j$(nproc)
```

The final output will be generated at:

```
output/images/rootfs.tar
```

This file is the **minimal Linux root filesystem**.

---

## 🐳 Create Distroless Docker Image

### Dockerfile

```dockerfile
FROM scratch
ADD rootfs.tar /
CMD ["/bin/sh"]
```

### Build Image

```bash
docker build -t my-distroless:arm64 .
```

### Run Container

```bash
docker run -it --rm my-distroless:arm64
```

If successful, you will enter a minimal BusyBox shell.

---

## 🔐 Security Characteristics

- No shell utilities beyond BusyBox
- No compiler or package manager
- Reduced libc attack surface (musl)
- Minimal filesystem footprint
- Suitable for:
  - Capability dropping
  - Read-only root filesystem
  - Seccomp profiles
  - No-new-privileges

Example hardened run:

```bash
docker run \
  --read-only \
  --cap-drop=ALL \
  --security-opt no-new-privileges \
  my-distroless:arm64
```

---

## 🚀 Golden Image Strategy

This image is intended to be used as a **base image**:

```dockerfile
FROM my-distroless:arm64
COPY myapp /usr/bin/myapp
CMD ["/usr/bin/myapp"]
```

Applications must be:
- Precompiled
- Preferably static
- Built using the same Buildroot toolchain

---

## 📦 Why Not Alpine / Ubuntu?

| Feature | Alpine | Ubuntu | This Project |
|------|--------|--------|-------------|
| Package manager | ✅ | ✅ | ❌ |
| Attack surface | Medium | High | **Minimal** |
| Reproducibility | Partial | Partial | **High** |
| Supply chain control | Low | Low | **High** |

---

## 🧪 Future Enhancements

- CI/CD pipeline integration
- SBOM generation
- Image signing (cosign)
- Seccomp & AppArmor profiles
- Kubernetes runtime hardening

---

## 📚 References

- Buildroot: https://buildroot.org
- musl libc: https://musl.libc.org
- BusyBox: https://busybox.net

---

