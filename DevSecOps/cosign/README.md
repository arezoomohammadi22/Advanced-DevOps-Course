# Cosign End-to-End Guide (Private Registry)

This guide documents **end‑to‑end usage of cosign** with a **private container registry** (`registry.sananetco.com`) based on real troubleshooting and production‑like scenarios.

It covers:
- Installing cosign
- Generating a key pair (key‑based signing)
- Correctly resolving image digests from a private registry
- Signing images
- Verifying signatures
- Offline / air‑gapped considerations
- Common pitfalls and fixes

---

## 1. What cosign Does (Context)

cosign is a container image signing tool from the Sigstore ecosystem. It provides:

- **Integrity**: guarantees the image has not been modified
- **Authenticity**: proves who signed the image
- **Supply‑chain security**: enables policy enforcement (CI/CD, Kubernetes)

cosign **always signs image digests**, never tags.

---

## 2. Prerequisites

- Linux server
- Docker installed and working
- Push access to `registry.sananetco.com`
- Internet access is **optional** (see offline notes)

Verify:
```bash
docker version
```

---

## 3. Install cosign

### Option A: Binary install (recommended)

```bash
COSIGN_VERSION=$(curl -s https://api.github.com/repos/sigstore/cosign/releases/latest | jq -r .tag_name)
wget https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-amd64
chmod +x cosign-linux-amd64
mv cosign-linux-amd64 /usr/local/bin/cosign
```

Verify:
```bash
cosign version
```

---

## 4. Login to the Private Registry

cosign uses **Docker credentials** to push signatures.

```bash
docker login registry.sananetco.com
```

You **must** have push permission on the repository.

---

## 5. Prepare an Image in Your Own Namespace

Never sign images in repositories you do not own (e.g. `library/nginx`).

Example:
```bash
docker pull nginx:latest
docker tag nginx:latest registry.sananetco.com/devops/nginx:latest
docker push registry.sananetco.com/devops/nginx:latest
```

---

## 6. Resolve the Correct Image Digest (CRITICAL)

Do **not** rely on `RepoDigests[0]` blindly. Images may contain multiple digests.

Correct command:
```bash
docker image inspect registry.sananetco.com/devops/nginx:latest \
  --format '{{range .RepoDigests}}{{println .}}{{end}}'
```

Example output:
```
registry.sananetco.com/devops/nginx@sha256:AAAA
nginx@sha256:BBBB
```

**Always use the digest that starts with your private registry**:
```
registry.sananetco.com/devops/nginx@sha256:AAAA
```

---

## 7. Generate a cosign Key Pair (Key‑Based Signing)

```bash
mkdir -p /root/cosign-keys
cd /root/cosign-keys

cosign generate-key-pair
```

You will be prompted for a password:

- The **private key** (`cosign.key`) is encrypted using this password
- The **public key** (`cosign.pub`) is not encrypted

Files created:
- `cosign.key` → private (keep secret)
- `cosign.pub` → public (used for verify)

---

## 8. Sign the Image (Offline / Private Mode)

Because private environments may not allow access to Sigstore TUF / Rekor, disable transparency log uploads.

```bash
cosign sign \
  --key /root/cosign-keys/cosign.key \
  --tlog-upload=false \
  registry.sananetco.com/devops/nginx@sha256:AAAA
```

What happens:
- The private key is decrypted in memory
- The image digest is cryptographically signed
- The signature is pushed as an OCI artifact into **your registry**

No external services are required in this mode.

---

## 9. Verify the Signature (Offline)

```bash
cosign verify \
  --key /root/cosign-keys/cosign.pub \
  --insecure-ignore-tlog=true \
  registry.sananetco.com/devops/nginx@sha256:AAAA
```

Expected result:
- Signature is valid
- Digest matches
- Image integrity confirmed

---

## 10. Where the Signature Is Stored

- The signature is stored **inside the same registry** as an OCI artifact
- It requires **push permission** on the repository
- No image layers are modified

Registry remains the single source of truth.

---

## 11. Common Errors and Their Meaning

### A) cosign tries to push to DockerHub

Example error:
```
POST https://index.docker.io/v2/library/nginx/blobs/uploads/: UNAUTHORIZED
```

Cause:
- You signed `nginx@sha256:...` instead of `registry.sananetco.com/...@sha256:...`

Fix:
- Always resolve and use the **private registry digest**

---

### B) TUF / sigstore 403 errors

Example:
```
failed to download tuf-repo-cdn.sigstore.dev
```

Cause:
- No internet access
- Firewall / proxy / sanctions

Fix:
- Use `--tlog-upload=false`
- Verify with `--insecure-ignore-tlog=true`

---

## 12. Internet Requirement Summary

| Mode | Internet Required |
|---|---|
| Keyless (OIDC) | Yes |
| Key‑based (default) | Yes (for Rekor) |
| Key‑based + `--tlog-upload=false` | No |

---

## 13. Recommended Practice for Private Registries

- Use **key‑based signing**
- Disable transparency log uploads
- Store keys securely
- Enforce verification in CI/CD or Kubernetes later

---

## 14. Final Notes

- cosign signs **digests**, not tags
- The registry must allow **push**, not just pull
- Signature ≠ image layer
- Rekor / transparency logs are optional

This setup is production‑safe for private, internal, or air‑gapped environments.

---


