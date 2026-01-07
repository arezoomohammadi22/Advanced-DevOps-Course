# Dockerfile Security Policies with Conftest (DevSecOps Lab)

This repository demonstrates how to use **Conftest** and **OPA / Rego** to enforce
security and best-practice policies on Dockerfiles.

All policies are evaluated automatically and will **fail the build / CI pipeline**
if a rule is violated.

---

## 🎯 Policies Included

This policy pack enforces the following rules:

1. **Disallow `latest` image tags**
2. **Block package managers (`apk`, `apt-get`, `yum`)**
3. **Enforce non-root users**
4. **Block `COPY . /`**

---

## 📁 Project Structure

```
conftest-lab/
├── Dockerfile
└── policy/
    ├── deny_latest.rego
    ├── deny_pkg_managers.rego
    ├── deny_root_user.rego
    └── deny_copy_all.rego
```

All policies are loaded automatically by Conftest.

---

## 🐳 Example Dockerfile (FAIL)

```dockerfile
FROM alpine:latest
RUN apk add --no-cache curl
COPY . /
```

This Dockerfile will fail because:
- Uses `latest`
- Uses `apk`
- Copies everything into the image
- Runs as root (no USER defined)

---

## 🧩 Policy Definitions

---

### 1️⃣ Disallow `latest` Image Tags

**File:** `policy/deny_latest.rego`

```rego
package main

# Implicit latest (no tag)
deny contains msg if {
  some i
  input[i].Cmd == "from"
  image := input[i].Value[0]
  not contains(image, ":")
  msg := sprintf("Image '%v' uses implicit 'latest' tag, which is not allowed", [image])
}

# Explicit latest
deny contains msg if {
  some i
  input[i].Cmd == "from"
  image := input[i].Value[0]
  parts := split(image, ":")
  tag := parts[count(parts) - 1]
  tag == "latest"
  msg := sprintf("Image '%v' uses forbidden 'latest' tag", [image])
}
```

---

### 2️⃣ Block Package Managers (`apk`, `apt-get`, `yum`)

**File:** `policy/deny_pkg_managers.rego`

```rego
package main

denylist := {"apk", "apt-get", "yum"}

deny contains msg if {
  some i
  input[i].Cmd == "run"
  runline := lower(input[i].Value[0])
  some bad in denylist
  contains(runline, bad)
  msg := sprintf("RUN contains forbidden package manager '%v': %v", [bad, runline])
}
```

---

### 3️⃣ Enforce Non-Root Users

**File:** `policy/deny_root_user.rego`

```rego
package main

# Explicit USER root
deny contains msg if {
  some i
  input[i].Cmd == "user"
  lower(input[i].Value[0]) == "root"
  msg := "Dockerfile explicitly sets USER root, which is not allowed"
}

# No USER instruction (implicit root)
deny contains msg if {
  not user_defined
  msg := "Dockerfile does not define a USER. Containers must not run as root"
}

user_defined if {
  some i
  input[i].Cmd == "user"
}
```

---

### 4️⃣ Block `COPY . /`

**File:** `policy/deny_copy_all.rego`

```rego
package main

deny contains msg if {
  some i
  input[i].Cmd == "copy"
  src := input[i].Value[0]
  dest := input[i].Value[1]
  src == "."
  dest == "/"
  msg := "COPY . / is not allowed. Copy only required files explicitly"
}
```

---

## ▶️ Running Conftest

Run all policies against a Dockerfile:

```bash
docker run --rm   -v "$(pwd)":/project   -w /project   openpolicyagent/conftest test   --policy policy/   Dockerfile
```

---

## ❌ Example Output (FAIL)

```text
FAIL - Dockerfile - main - Image 'alpine:latest' uses forbidden 'latest' tag
FAIL - Dockerfile - main - RUN contains forbidden package manager 'apk'
FAIL - Dockerfile - main - COPY . / is not allowed. Copy only required files explicitly
FAIL - Dockerfile - main - Dockerfile does not define a USER. Containers must not run as root
```

---

## ✅ Example Dockerfile (PASS)

```dockerfile
FROM alpine:3.19
RUN adduser -D appuser
USER appuser
COPY app/ /app/
```

---

## 🔍 Debugging: Inspect Parsed Input

```bash
docker run --rm   -v "$(pwd)":/project   -w /project   openpolicyagent/conftest parse Dockerfile
```

Use this output to understand how Dockerfile instructions are represented in Rego.

---

## 🚀 CI/CD Usage

Use the same command in your CI pipeline (GitLab CI, GitHub Actions, Jenkins).

If any policy fails:
- The pipeline fails
- The image is not built
- Security issues are caught early

---

## 🧠 Key Takeaways

- Policy-as-Code enables **fail-fast security**
- Dockerfile security rules become enforceable standards
- No manual review required
- Policies scale across teams and repositories

---

