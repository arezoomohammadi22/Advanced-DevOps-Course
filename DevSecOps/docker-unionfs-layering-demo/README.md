# Docker Layering Explained with UnionFS & OverlayFS (Hands-on)

This repository demonstrates **how Docker image and container layers work internally** using
**Union Filesystems**, implemented manually in two ways:

1. **UnionFS-FUSE** (educational, userspace, concept-first)
2. **OverlayFS** (kernel-based, closest to Docker `overlay2`)

The goal is to *visually and practically* understand:
- Read-only image layers
- Writable container layer
- Copy-on-Write (CoW)
- Layer overriding and sharing
- How Docker "commit" conceptually works

---

## Core Concept: Union Filesystem

A **Union Filesystem** allows multiple directories (layers) to appear as **one filesystem**.

Rules:
- Lower layers → **read-only**
- Top layer → **read-write**
- If a file exists in multiple layers → **topmost layer wins**
- Writes always go to the **upper (writable) layer**

Docker uses this exact idea.

Example Docker-like structure:

```
Base Image Layer      (read-only)
Application Layer     (read-only)
-------------------------------
Container Layer       (read-write)
```

---

# Method 1: UnionFS-FUSE (User-space, Teaching Friendly)

This method is perfect for **education and demos**.

### 1. Install Requirements
```bash
sudo apt update
sudo apt install -y unionfs-fuse fuse
sudo modprobe fuse
lsmod | grep fuse
```

### 2. Create Layer Directories
```bash
sudo mkdir -p /mnt/ufs-demo/{base,upper,merged}
```

- `base`   → read-only layer (image)
- `upper`  → writable layer (container)
- `merged` → unified mount (container rootfs)

### 3. Create Base Files (Read-Only Layer)
```bash
echo "I am base file 1" | sudo tee /mnt/ufs-demo/base/1
mkdir -p /mnt/ufs-demo/base/app
echo "hello from base" | sudo tee /mnt/ufs-demo/base/app/hello.txt
```

### 4. Mount UnionFS
```bash
sudo unionfs-fuse -o cow /mnt/ufs-demo/upper=RW:/mnt/ufs-demo/base=RO /mnt/ufs-demo/merged
```

> `-o cow` enables **Copy-on-Write**, same behavior as Docker.

### 5. Test Behavior
```bash
ls /mnt/ufs-demo/base
ls /mnt/ufs-demo/merged
```

Create a new file inside merged:
```bash
echo "new file" | sudo tee /mnt/ufs-demo/merged/d
```

Check layers:
```bash
ls /mnt/ufs-demo/base     # unchanged
ls /mnt/ufs-demo/upper    # new file exists
ls /mnt/ufs-demo/merged   # sees both
```

### 6. Override Existing File
```bash
echo "OVERRIDDEN" | sudo tee /mnt/ufs-demo/merged/1
cat /mnt/ufs-demo/base/1
cat /mnt/ufs-demo/upper/1
cat /mnt/ufs-demo/merged/1
```

### 7. Unmount
```bash
sudo umount /mnt/ufs-demo/merged
```

---

# Method 2: OverlayFS (Kernel-based, Docker-like)

Docker on Linux uses **overlay2**, which is based on **OverlayFS**.

### 1. Create Directories
```bash
sudo mkdir -p /mnt/ovl-demo/{lower,upper,work,merged}
```

- `lower` → image layer
- `upper` → container writable layer
- `work`  → required by kernel
- `merged` → container filesystem

### 2. Create Base File
```bash
echo "base file" | sudo tee /mnt/ovl-demo/lower/1
```

### 3. Mount OverlayFS
```bash
sudo mount -t overlay overlay \
  -o lowerdir=/mnt/ovl-demo/lower,upperdir=/mnt/ovl-demo/upper,workdir=/mnt/ovl-demo/work \
  /mnt/ovl-demo/merged
```

### 4. Test Write
```bash
echo "new file" | sudo tee /mnt/ovl-demo/merged/d
ls /mnt/ovl-demo/lower
ls /mnt/ovl-demo/upper
```

### 5. File Override
```bash
echo "changed" | sudo tee /mnt/ovl-demo/merged/1
cat /mnt/ovl-demo/lower/1
cat /mnt/ovl-demo/upper/1
```

### 6. File Deletion (Whiteout)
```bash
sudo rm /mnt/ovl-demo/merged/1
ls /mnt/ovl-demo/merged
ls /mnt/ovl-demo/lower
ls /mnt/ovl-demo/upper
```

OverlayFS uses **whiteout files** to hide lower-layer files.

### 7. Unmount
```bash
sudo umount /mnt/ovl-demo/merged
```

---

## Docker Commit Concept (Layer Stacking)

Docker does NOT modify old layers.

Instead:
1. Upper layer becomes **new read-only layer**
2. A fresh upper layer is created
3. Layers stack with hashes and IDs

### Manual Simulation
```bash
sudo cp -a /mnt/ovl-demo/upper /mnt/ovl-demo/layer1
```

Then remount with multiple lower layers:
```bash
sudo mount -t overlay overlay \
  -o lowerdir=/mnt/ovl-demo/layer1:/mnt/ovl-demo/lower,upperdir=/mnt/ovl-demo/upper2,workdir=/mnt/ovl-demo/work2 \
  /mnt/ovl-demo/merged
```

This perfectly demonstrates Docker layer stacking.

---

## Key Takeaways

- Docker images are **immutable**
- Containers add **one writable layer**
- UnionFS/OverlayFS enable:
  - Layer reuse
  - Caching
  - Fast container startup
- OverlayFS is what Docker actually uses on Linux

---

## Recommended GitHub Repository Names

- `docker-unionfs-layering-demo`
- `docker-filesystem-layers-explained`
- `container-layering-from-scratch`
- `overlayfs-vs-unionfs-docker`
- ⭐ **`docker-layering-deep-dive`** (Recommended)

