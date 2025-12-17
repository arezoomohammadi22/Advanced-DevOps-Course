# Exposing Kibana with Traefik (HTTP → HTTPS)

This README explains how to expose **Kibana (installed via ECK)** using **Traefik CRDs** with:
- HTTP entryPoint (`web`) → redirect to HTTPS
- HTTPS entryPoint (`websecure`) → proxy to Kibana
- Handling Kibana self‑signed TLS using `ServersTransport`

---

## Architecture Overview

```
Browser
  ├── http://kibana.sananetco.com:30080
  │        └── Traefik (web) → redirect-to-https
  └── https://kibana.sananetco.com:30443
           └── Traefik (websecure)
                └── Kibana Service (ClusterIP:5601)
```

---

## Prerequisites

- Traefik installed with CRDs enabled
- Traefik entryPoints:
  - `web` (NodePort 30080)
  - `websecure` (NodePort 30443)
- Kibana deployed via ECK
- Kibana service exists:
  ```bash
  kubectl get svc -n default kibana-logging-kb-http
  ```

---

## 1) ServersTransport (Kibana TLS handling)

Kibana deployed by ECK uses a **self‑signed TLS certificate**.
Traefik must skip upstream TLS verification.

### `kibana-serverstransport.yaml`
```yaml
apiVersion: traefik.io/v1alpha1
kind: ServersTransport
metadata:
  name: kibana-insecure
  namespace: default
spec:
  insecureSkipVerify: true
```

Apply:
```bash
kubectl apply -f kibana-serverstransport.yaml
```

---

## 2) Middleware (HTTP → HTTPS redirect)

### `redirect-to-https.yaml`
```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: redirect-to-https
  namespace: default
spec:
  redirectScheme:
    scheme: https
    permanent: true
```

Apply:
```bash
kubectl apply -f redirect-to-https.yaml
```

---

## 3) IngressRoute (HTTP – web)

All HTTP traffic is redirected to HTTPS.

### `kibana-http.yaml`
```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: kibana-http
  namespace: default
spec:
  entryPoints:
    - web
  routes:
    - kind: Rule
      match: Host(`kibana.sananetco.com`)
      middlewares:
        - name: redirect-to-https
      services:
        - name: kibana-logging-kb-http
          port: 5601
```

Apply:
```bash
kubectl apply -f kibana-http.yaml
```

---

## 4) IngressRoute (HTTPS – websecure)

This route terminates TLS at Traefik and proxies securely to Kibana.

### `kibana-https.yaml`
```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: kibana-https
  namespace: default
spec:
  entryPoints:
    - websecure
  routes:
    - kind: Rule
      match: Host(`kibana.sananetco.com`)
      services:
        - name: kibana-logging-kb-http
          port: 5601
          scheme: https
          serversTransport: kibana-insecure
  tls: {}
```

Apply:
```bash
kubectl apply -f kibana-https.yaml
```

---

## 5) Verification

### List Traefik CRDs
```bash
kubectl get ingressroute,middleware,serverstransport -n default
```

### Check Traefik logs
```bash
kubectl -n traefik logs deploy/traefik --tail=200 | egrep -i "kibana|error|tls"
```

---

## 6) Testing

### Get node IP
```bash
kubectl get nodes -o wide
```

Assume `<NODE-IP>`.

### HTTP (should redirect)
```bash
curl -I -H "Host: kibana.sananetco.com" http://<NODE-IP>:30080
```

### HTTPS (should return 302 → login)
```bash
curl -Ik -H "Host: kibana.sananetco.com" https://<NODE-IP>:30443
```

---

## 7) Browser Access

Add to `/etc/hosts`:
```
<NODE-IP> kibana.sananetco.com
```

Open:
```
https://kibana.sananetco.com:30443
```

> A certificate warning is expected unless a trusted TLS cert is configured.

---

## Notes

- Keep Kibana Service as `ClusterIP`
- Expose externally only via Traefik
- For production, replace `tls: {}` with a real certificate (cert‑manager / ACME)

---

## Summary

| Component | Purpose |
|---------|--------|
| ServersTransport | Handle Kibana self‑signed TLS |
| Middleware | Force HTTPS |
| IngressRoute (web) | Redirect HTTP |
| IngressRoute (websecure) | Secure access to Kibana |

