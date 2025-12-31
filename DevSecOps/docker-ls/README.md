# Docker TLS (mTLS) Setup with OpenSSL

This guide documents **exactly the commands used** to secure Docker Engine with **mutual TLS (mTLS)** using OpenSSL.
It is suitable for GitHub documentation and reproducible setups.

---

## Architecture

- Custom Certificate Authority (CA)
- Docker daemon secured on **TCP :2376**
- Client authentication using client certificates
- Docker daemon listens on:
  - Unix socket
  - TLS-secured TCP socket

---

## 1. Generate Certificate Authority (CA)

```bash
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -days 365 -key ca-key.pem -sha256 -out ca.pem
```

---

## 2. Generate Server Certificate

### Server private key
```bash
openssl genrsa -out server-key.pem 4096
```

### Server CSR
```bash
export DOCKER_HOSTNAME=localhost
openssl req -subj "/CN=$DOCKER_HOSTNAME" -new -key server-key.pem -out server.csr
```

### SAN configuration
```bash
echo "subjectAltName = DNS:$DOCKER_HOSTNAME,IP:127.0.0.1" > extfile.cnf
```

### Sign server certificate
```bash
openssl x509 -req -days 365 -sha256   -in server.csr   -CA ca.pem   -CAkey ca-key.pem   -CAcreateserial   -out server-cert.pem   -extfile extfile.cnf
```

---

## 3. Generate Client Certificate

### Client private key
```bash
openssl genrsa -out client-key.pem 4096
```

### Client CSR
```bash
openssl req -subj '/CN=docker-client' -new -key client-key.pem -out client.csr
```

### Sign client certificate
```bash
openssl x509 -req -days 365 -sha256   -in client.csr   -CA ca.pem   -CAkey ca-key.pem   -CAcreateserial   -out client-cert.pem
```

---

## 4. Secure Permissions (Required)

```bash
chmod 400 ca-key.pem
chmod 400 server-key.pem
chmod 400 client-key.pem

chmod 444 ca.pem
chmod 444 server-cert.pem
chmod 444 client-cert.pem
```

---

## 5. Docker TLS Directory

```bash
sudo mkdir -p /etc/docker/ssl
sudo mv server-key.pem server-cert.pem /etc/docker/ssl/
sudo cp ca.pem /etc/docker/ssl/
```

---

## 6. Docker Daemon Configuration

### `/etc/docker/daemon.json`

```json
{
  "tls": true,
  "tlsverify": true,
  "tlscacert": "/etc/docker/ssl/ca.pem",
  "tlscert": "/etc/docker/ssl/server-cert.pem",
  "tlskey": "/etc/docker/ssl/server-key.pem"
}
```

---

## 7. systemd Override (IMPORTANT)

Docker already defines a host (`fd://`).  
To avoid conflict, we override `ExecStart`.

```bash
sudo systemctl edit docker
```

Paste:

```ini
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd -H fd:// -H tcp://0.0.0.0:2376 --containerd=/run/containerd/containerd.sock
```

Apply changes:

```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
sudo systemctl status docker
```

---

## 8. Client Test

```bash
docker --tlsverify   --tlscacert=ca.pem   --tlscert=client-cert.pem   --tlskey=client-key.pem   -H tcp://localhost:2376 version
```

Successful output confirms:
- TLS enabled
- Client certificate validated
- Docker daemon reachable over TCP

---

## Common Issues

### Docker fails to start
Cause:
- `hosts` defined both in systemd and `daemon.json`

Fix:
- Do **NOT** define `"hosts"` in `daemon.json`

---

### Certificate mismatch
Verify key & cert match:

```bash
openssl x509 -noout -modulus -in server-cert.pem | openssl md5
openssl rsa  -noout -modulus -in server-key.pem  | openssl md5
```

Hashes must match.

---

## Result

- Docker Engine secured with **mutual TLS**
- Remote access allowed only with valid client cert
- Production-grade setup for:
  - GitLab Runner
  - Remote Docker API
  - Secure CI/CD

---

