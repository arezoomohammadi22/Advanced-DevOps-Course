# cert-manager Installation & Usage Guide (Cloudflare DNS-01)

This README explains **how to install cert-manager**, configure it with **Cloudflare DNS-01**, and **verify certificate issuance** using Kubernetes.

This guide is **self-contained** and does **not depend on Ingress, MetalLB, or LoadBalancers**.

---

## Prerequisites

- Kubernetes cluster (v1.24+ recommended)
- `kubectl` configured
- A domain managed by **Cloudflare**
- Cloudflare **API Token** with DNS edit permissions

---

## 1. Install cert-manager

Install cert-manager using the official manifest (includes CRDs):

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.4/cert-manager.yaml
```

Wait until all components are running:

```bash
kubectl get pods -n cert-manager
```

Expected pods:
- cert-manager
- cert-manager-webhook
- cert-manager-cainjector

All must be in `Running` state.

---

## 2. Create Cloudflare API Token

In Cloudflare dashboard:

1. Go to **My Profile → API Tokens**
2. Create token using template: **Edit zone DNS**
3. Permissions:
   - Zone → DNS → Edit
4. Zone Resources:
   - Include → Specific zone → your domain

Copy the generated token.

---

## 3. Store Cloudflare Token as Kubernetes Secret

```bash
kubectl create secret generic cloudflare-api-token-secret   --namespace cert-manager   --from-literal=api-token=YOUR_CLOUDFLARE_API_TOKEN
```

Verify:

```bash
kubectl get secret cloudflare-api-token-secret -n cert-manager
```

---

## 4. Create ClusterIssuer (Let’s Encrypt + Cloudflare)

Create file `clusterissuer-cloudflare.yaml`:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-cloudflare
spec:
  acme:
    email: your-real-email@example.com
    server: https://acme-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: letsencrypt-cloudflare-key
    solvers:
    - dns01:
        cloudflare:
          apiTokenSecretRef:
            name: cloudflare-api-token-secret
            key: api-token
```

Apply it:

```bash
kubectl apply -f clusterissuer-cloudflare.yaml
```

Check status:

```bash
kubectl get clusterissuer
kubectl describe clusterissuer letsencrypt-cloudflare
```

`READY` must be `True`.

---

## 5. Test Certificate Issuance (DNS-01)

Create file `test-certificate.yaml`:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: test-cert
  namespace: default
spec:
  secretName: test-cert-tls
  issuerRef:
    name: letsencrypt-cloudflare
    kind: ClusterIssuer
  dnsNames:
  - test.example.com
```

Apply:

```bash
kubectl apply -f test-certificate.yaml
```

---

## 6. Verify Certificate Status

Check certificate:

```bash
kubectl describe certificate test-cert
```

Expected:
- Status: `Ready = True`
- Secret created successfully

Check Orders:

```bash
kubectl get orders.acme.cert-manager.io
```

(Optional) Challenges may disappear quickly after success.

---

## 7. Verify Secret Content

```bash
kubectl get secret test-cert-tls -n default
```

Decode and inspect certificate:

```bash
kubectl get secret test-cert-tls -n default -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -text
```

Secret contains:
- `tls.crt`
- `tls.key`

---

## 8. Wildcard Certificate Example (Optional)

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: wildcard-cert
  namespace: default
spec:
  secretName: wildcard-cert-tls
  issuerRef:
    name: letsencrypt-cloudflare
    kind: ClusterIssuer
  dnsNames:
  - "*.example.com"
  - "example.com"
```

DNS-01 is **required** for wildcard certificates.

---

## 9. Useful Debug Commands

cert-manager logs:

```bash
kubectl logs -n cert-manager deploy/cert-manager
```

List ACME resources:

```bash
kubectl get certificaterequests
kubectl get orders.acme.cert-manager.io
kubectl get challenges.acme.cert-manager.io
```

---

## 10. Common Errors

| Error | Cause |
|-----|------|
| ClusterIssuer not Ready | Invalid email or ACME registration failed |
| No TXT record created | Cloudflare token permission issue |
| Certificate Pending | DNS zone mismatch |
| Forbidden domain | Using example.com as email |

---

## Result

You now have:
- cert-manager installed
- Cloudflare DNS-01 configured
- Automatic certificate issuance & renewal
- Support for wildcard certificates

---

## References

- https://cert-manager.io/docs/
- https://letsencrypt.org/docs/
- https://developers.cloudflare.com/api/

