# Trivy Installation & Usage Guide (ARM64 / Debian-based Linux)

This README explains **how to install Trivy using the official APT repository**, how to **use it effectively**, and **how it works internally** so scan results actually make sense.

Tested and suitable for **ARM64 (aarch64)** systems.

---

## 1. What is Trivy?

**Trivy** is a **container and artifact security scanner** that can detect:

- Vulnerabilities (CVE)
- Secrets (API keys, tokens, passwords)
- Misconfigurations (Dockerfile, Kubernetes, IaC)
- Software Bill of Materials (SBOM)

It is widely used in **DevSecOps pipelines** because it is:
- Fast
- Easy to automate
- Actively maintained

---

## 2. Installation (APT Repository – Recommended)

This method installs Trivy from the **official Aqua Security repository**.

### 2.1 Install prerequisites
```bash
sudo apt-get install -y wget gnupg
```

---

### 2.2 Add Trivy GPG key
```bash
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | \
  gpg --dearmor | sudo tee /usr/share/keyrings/trivy.gpg > /dev/null
```

This ensures:
- Package authenticity
- Protection against tampered binaries

---

### 2.3 Add Trivy APT repository
```bash
echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb generic main" | \
  sudo tee /etc/apt/sources.list.d/trivy.list
```

---

### 2.4 Update package index
```bash
sudo apt-get update
```

---

### 2.5 Install Trivy
```bash
sudo apt-get install -y trivy
```

---

### 2.6 Verify installation
```bash
trivy version
```

Expected output:
```text
Version: 0.xx.x
OS: linux
Arch: arm64
```

---

## 3. First Run (Important)

On first execution, Trivy will:
- Download its vulnerability database
- Store it locally
- This may take time and disk space (hundreds of MB)

This is **normal and required**.

Database location:
```text
~/.cache/trivy/db
```

---

## 4. Basic Usage

### 4.1 Scan a container image (default)
```bash
trivy image nginx:latest
```

This performs:
- Vulnerability scan
- OS packages + application dependencies

---

### 4.2 Vulnerability-only scan (recommended for CI)
```bash
trivy image \
  --scanners vuln \
  nginx:latest
```

Why use this?
- Faster
- Focused
- Less noise

---

### 4.3 Save scan result as JSON
```bash
trivy image \
  --scanners vuln \
  --format json \
  --output report.json \
  nginx:latest
```

This is useful for:
- Automation
- CI/CD
- Post-processing

---

### 4.4 Filter by severity
```bash
trivy image \
  --severity HIGH,CRITICAL \
  nginx:latest
```

Severity levels:
- UNKNOWN
- LOW
- MEDIUM
- HIGH
- CRITICAL

---

### 4.5 Fail on critical vulnerabilities (CI style)
```bash
trivy image \
  --severity CRITICAL \
  --exit-code 1 \
  nginx:latest
```

Behavior:
- Exit code = 1 if CRITICAL found
- Exit code = 0 otherwise

---

### 4.6 Skip DB update (faster repeated scans)
```bash
trivy image \
  --skip-db-update \
  nginx:latest
```

Use this only when:
- DB is already up-to-date
- Running multiple scans in a short time

---

## 5. Understanding Trivy Output

Each vulnerability entry includes:

- CVE ID
- Severity
- Affected package
- Installed version
- Fixed version (if available)

Important:
> Not every CVE means the image is exploitable.
> Trivy reports **known risk**, not confirmed compromise.

---

## 6. How Trivy Works (Internals)

Trivy scanning process:

1. Pulls or inspects image layers
2. Identifies OS and packages
3. Matches packages against CVE database
4. Reports known vulnerabilities

CVE database:
- Updated frequently
- Essential for accurate results
- Outdated DB = useless scan

---

## 7. What Trivy Does NOT Do

Trivy:
- ❌ Does not exploit vulnerabilities
- ❌ Does not check runtime behavior
- ❌ Does not replace runtime security

It is a **prevention and visibility tool**, not a runtime IDS.

---

## 8. Best Practices

- Use `--scanners vuln` in CI
- Fail builds only on HIGH/CRITICAL
- Combine with:
  - Image signing (cosign)
  - Admission control
  - Runtime protections (seccomp, AppArmor)

---

## 9. Common Issues

### Database download is slow
- First run is always slow
- Subsequent runs are faster

### Too many vulnerabilities
- Use minimal base images
- Update packages
- Filter by severity

---

**End of README**

