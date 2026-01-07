# Conftest – Dockerfile Policy Check (DevSecOps Lab)

This lab demonstrates how to use **Conftest** with **OPA / Rego** to enforce security policies on Dockerfiles and automatically fail builds when policies are violated.

---

## 🎯 Lab Objectives

- Understand **Policy-as-Code** for Dockerfiles
- Enforce security rules during Docker image build time
- Detect and block forbidden commands (e.g. `apk`, `apt-get`, `yum`)
- Automatically fail CI pipelines on policy violations
- Learn how Conftest parses Dockerfiles

---

## 📂 Project Structure

```
conftest-lab/
├── Dockerfile
├── policy/
│   └── dockerfile.rego
└── README.md
```

---

## 🐳 Dockerfile Under Test

```dockerfile
FROM alpine:3.19
RUN apk add --no-cache curl
```

This Dockerfile installs packages using `apk`, which is **intentionally forbidden** by our policy.

---

## 🔐 Policy Definition (Rego)

File: `policy/dockerfile.rego`

```rego
package main

denylist := {"apt-get", "apk", "yum"}

deny contains msg if {
  some i
  input[i].Cmd == "run"

  # In this setup, RUN commands are parsed as a single string
  # Example: ["apk add --no-cache curl"]
  runline := lower(input[i].Value[0])

  some bad in denylist
  contains(runline, bad)

  msg := sprintf("RUN contains forbidden tool '%v': %v", [bad, runline])
}
```

### 🔎 What This Policy Does

- Iterates over Dockerfile instructions
- Matches only `RUN` commands
- Converts the RUN command to lowercase
- Checks if it contains any forbidden package managers
- Produces a **deny message** if a match is found

---

## ▶️ Running the Policy Check

Run Conftest using the official Docker image:

```bash
docker run --rm \
  -v "$(pwd)":/project \
  -w /project \
  openpolicyagent/conftest test \
  --policy policy/ \
  Dockerfile
```

---

## ❌ Expected Output (FAIL)

```text
FAIL - Dockerfile - main - RUN contains forbidden tool 'apk': apk add --no-cache curl

1 test, 0 passed, 0 warnings, 1 failure, 0 exceptions
```

This confirms:
- The policy was successfully loaded
- The Dockerfile was evaluated
- The forbidden command was detected
- The test correctly failed

---

## 🔍 Inspecting Parsed Dockerfile Input

To understand how Conftest interprets Dockerfiles, run:

```bash
docker run --rm \
  -v "$(pwd)":/project \
  -w /project \
  openpolicyagent/conftest parse Dockerfile
```

### Parsed Output

```json
[
  [
    {
      "Cmd": "from",
      "Value": ["alpine:3.19"]
    },
    {
      "Cmd": "run",
      "Value": ["apk add --no-cache curl"]
    }
  ]
]
```

### ⚠️ Important Note

- `Value` is an **array**, but each `RUN` instruction is represented as a **single string**
- This is why the policy checks `Value[0]` and uses `contains()`

---

## 🚦 Why This Policy Matters

This policy prevents:

- Non-reproducible builds
- Hidden dependency installation
- Supply-chain risks
- Unauthorized package managers

It enforces **secure, auditable, and controlled image builds**.

---

## 🔁 CI/CD Usage

This same command can be used inside CI pipelines (GitLab CI, GitHub Actions, Jenkins).

If the policy fails:
- The pipeline fails
- The image is not built
- The violation is visible immediately

---

## 🧠 Key Takeaways

- Conftest enables **fail-fast security enforcement**
- Policies must match the **real parsed input shape**
- `parse` is essential for debugging policies
- Policy-as-Code removes manual review bottlenecks

---



