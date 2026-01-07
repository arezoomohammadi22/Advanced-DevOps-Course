# Conftest Dockerfile Policy: Disallow `latest` Image Tags

This lab shows how to use **Conftest** (OPA/Rego) to **block Dockerfiles that use `:latest`** (or omit a tag, which implies `latest`).

---

## ✅ What this policy checks

It will **FAIL** a Dockerfile when:

- `FROM image:latest` is used (explicit latest)
- `FROM image` is used (no tag → implicit latest)

---

## 📁 Recommended project structure

```
conftest-lab/
├── Dockerfile
└── policy/
    └── deny_latest.rego
```

---

## 🧩 Policy file

Create: `policy/deny_latest.rego`

```rego
package main

# Deny implicit latest (no tag specified)
deny contains msg if {
  some i
  input[i].Cmd == "from"
  image := input[i].Value[0]

  not contains(image, ":")

  msg := sprintf("Image '%v' uses implicit 'latest' tag, which is not allowed", [image])
}

# Deny explicit latest
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

> **Why `package main`?**  
> By default, Conftest evaluates `data.main.deny`. If you use another package name (e.g. `package dockerfile`),
> you must run Conftest with `--namespace dockerfile`. Using `main` is the simplest approach for labs and CI.

---

## 🧪 Test cases

### 1) Expected FAIL (explicit latest)

`Dockerfile`:

```dockerfile
FROM alpine:latest
```

Run:

```bash
docker run --rm \
  -v "$(pwd)":/project \
  -w /project \
  openpolicyagent/conftest test \
  --policy policy/ \
  Dockerfile
```

Expected output (example):

```text
FAIL - Dockerfile - main - Image 'alpine:latest' uses forbidden 'latest' tag
```

---

### 2) Expected FAIL (implicit latest)

`Dockerfile`:

```dockerfile
FROM alpine
```

Expected output (example):

```text
FAIL - Dockerfile - main - Image 'alpine' uses implicit 'latest' tag, which is not allowed
```

---

### 3) Expected PASS

`Dockerfile`:

```dockerfile
FROM alpine:3.19
```

Expected output:

```text
1 test, 1 passed, 0 warnings, 0 failures, 0 exceptions
```

---

## 🔍 Debug tip: see Conftest parsed input

```bash
docker run --rm \
  -v "$(pwd)":/project \
  -w /project \
  openpolicyagent/conftest parse Dockerfile
```

This helps you confirm how `FROM` lines are represented in `input` so your Rego matches the real input shape.

---

## ✅ CI/CD usage

Use the same command in your pipeline. If the policy fails, the pipeline fails:

```bash
docker run --rm -v "$PWD":/project -w /project openpolicyagent/conftest test --policy policy/ Dockerfile
```

---

