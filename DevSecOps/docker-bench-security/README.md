# Docker Bench for Security
## Installation, Usage, and Result Analysis (Practical Guide)

This guide explains how to install, run, and analyze **Docker Bench for Security**
based on real execution on a production-like server (e.g. GitLab Runner host).

Docker Bench for Security checks your Docker host against the **CIS Docker Benchmark**
and reports configuration issues.

---

## 1. What is Docker Bench for Security?

Docker Bench for Security is an **audit tool**, not a vulnerability scanner.

It:
- Audits Docker daemon configuration
- Audits host configuration
- Audits running containers
- Outputs PASS / WARN / INFO / NOTE
- Does **not modify** the system

---

## 2. Method 1 — Run Using Docker (Containerized)

```bash
docker run --rm -it   --net host   --pid host   --userns host   --cap-add audit_control   -v /etc:/etc:ro   -v /usr/bin/containerd:/usr/bin/containerd:ro   -v /usr/bin/runc:/usr/bin/runc:ro   -v /usr/lib/systemd:/usr/lib/systemd:ro   -v /lib/systemd/system:/lib/systemd/system:ro   -v /var/lib:/var/lib:ro   -v /var/run/docker.sock:/var/run/docker.sock:ro   docker/docker-bench-security
```

Use this only with trusted images.

---

## 3. Method 2 — Recommended: Run Directly on the Host

```bash
git clone https://github.com/docker/docker-bench-security.git
cd docker-bench-security
sudo ./docker-bench-security.sh
```

This avoids container mount conflicts and is the most stable approach.

---

## 4. Understanding the Output

| Status | Meaning |
|------|--------|
| PASS | Secure configuration |
| WARN | Security issue detected |
| INFO | Informational |
| NOTE | Manual review needed |

---

## 5. High-Risk Findings to Fix First

- Docker socket mounted in containers
- Containers running as root
- no-new-privileges disabled
- No CPU / Memory / PID limits
- Writable root filesystem

---

## 6. Analysis Example

```text
[WARN] 5.32 - Docker socket shared
```

This means the container can control the Docker daemon and potentially the host.

---

## 7. Re-run After Fixes

```bash
sudo ./docker-bench-security.sh
```

Compare WARN counts before and after changes.

---

## 8. What Docker Bench Does NOT Do

- Does not scan CVEs
- Does not detect malware
- Does not monitor runtime behavior

Use alongside Trivy, image signing, and runtime hardening.

---

## 9. Summary

Docker Bench for Security provides a **baseline security audit**.
Treat WARN results as actionable items.

---

End of README
