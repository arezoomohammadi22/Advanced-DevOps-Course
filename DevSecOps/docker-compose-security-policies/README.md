# Docker Compose Security Policies with Conftest (DevSecOps)

## 📦 Recommended GitHub Repository Name

**`docker-compose-security-policies`**

Alternative names:
- `compose-devsecops-policies`
- `conftest-docker-compose-policies`
- `docker-compose-policy-pack`

---

## 🎯 Purpose of This Repository

This repository demonstrates how to use **Conftest** and **Open Policy Agent (OPA / Rego)**
to enforce **security best practices on Docker Compose files**.

All policies are evaluated automatically.  
If any rule is violated, **the test and CI pipeline will fail**.

---

## ✅ Policies Included

This policy pack enforces the following rules on `docker-compose.yml`:

1. 🚫 Disallow `privileged: true`
2. 🚫 Block mounting Docker socket (`/var/run/docker.sock`)
3. 🚫 Disallow `network_mode: host`
4. 🚫 Disallow `latest` image tags (explicit and implicit)

---

## 📁 Repository Structure

```
docker-compose-security-policies/
├── docker-compose.yml
└── policy/
    └── compose/
        ├── deny_privileged.rego
        ├── deny_docker_sock.rego
        ├── deny_host_network.rego
        └── deny_latest_images.rego
```

---

## ▶️ How to Run the Policies

Run all policies against a Docker Compose file:

```bash
docker run --rm \
  -v "$(pwd)":/project \
  -w /project \
  openpolicyagent/conftest test \
  --policy policy/compose/ \
  docker-compose.yml
```

---

## 🔍 Debugging (Inspect Parsed Input)

To understand how Conftest parses `docker-compose.yml`:

```bash
docker run --rm \
  -v "$(pwd)":/project \
  -w /project \
  openpolicyagent/conftest parse docker-compose.yml
```

This is extremely useful when writing or debugging policies.

---

## 🧩 Policy Definitions

---

### 1️⃣ Disallow Privileged Containers

**File:** `policy/compose/deny_privileged.rego`

```rego
package main

deny contains msg if {
  some svc
  input.services[svc].privileged == true
  msg := sprintf("Service '%v' uses privileged=true (not allowed)", [svc])
}
```

---

### 2️⃣ Block Docker Socket Mount

**File:** `policy/compose/deny_docker_sock.rego`

```rego
package main

deny contains msg if {
  some svc
  some i
  vol := input.services[svc].volumes[i]
  contains(lower(vol), "/var/run/docker.sock")
  msg := sprintf("Service '%v' mounts docker.sock (not allowed): %v", [svc, vol])
}
```

---

### 3️⃣ Disallow Host Network Mode

**File:** `policy/compose/deny_host_network.rego`

```rego
package main

deny contains msg if {
  some svc
  input.services[svc].network_mode == "host"
  msg := sprintf("Service '%v' uses network_mode=host (not allowed)", [svc])
}
```

---

### 4️⃣ Disallow `latest` Image Tags

**File:** `policy/compose/deny_latest_images.rego`

```rego
package main

# Explicit latest (image: repo/name:latest)
deny contains msg if {
  some svc
  image := input.services[svc].image
  parts := split(image, ":")
  count(parts) > 1
  tag := parts[count(parts)-1]
  tag == "latest"
  msg := sprintf("Service '%v' uses forbidden image tag ':latest' -> %v", [svc, image])
}

# Implicit latest (image without tag)
deny contains msg if {
  some svc
  image := input.services[svc].image
  not contains(image, ":")
  msg := sprintf("Service '%v' uses implicit latest tag (no tag specified) -> %v", [svc, image])
}
```

---

## ❌ Example docker-compose.yml (FAIL)

```yaml
services:
  app:
    image: alpine:latest
    privileged: true
    network_mode: host
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

### Expected output:
Multiple FAIL messages (latest, privileged, host network, docker.sock).

---

## ✅ Example docker-compose.yml (PASS)

```yaml
services:
  app:
    image: alpine:3.19
    command: ["sh", "-c", "echo secure"]
```

---

## 🚀 CI/CD Usage

Use the same command inside CI pipelines (GitHub Actions, GitLab CI, Jenkins).

If any policy fails:
- The pipeline fails
- The compose stack is blocked
- Security issues are caught early

---

## 🧠 Key Takeaways

- Docker Compose can and should be secured
- Policy-as-Code removes manual reviews
- Conftest enables fail-fast DevSecOps
- These rules scale across teams and repositories

---

**Tooling:** Conftest + Open Policy Agent (OPA)  
**Scope:** Docker Compose Security Policies  
**Goal:** Secure-by-default container orchestration
