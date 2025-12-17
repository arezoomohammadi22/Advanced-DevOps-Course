# Install Traefik on Kubernetes using Helm (NodePort)

This guide installs **Traefik** as an Ingress Controller on a Kubernetes cluster using **Helm**, matching your exact command and explaining every `--set` value.

---

## Prerequisites

- Kubernetes cluster up and reachable (`kubectl` works)
- Helm installed (`helm version`)
- You have permission to create namespaces and install cluster resources

---

## 1) Add the Traefik Helm repository

```bash
helm repo add traefik https://traefik.github.io/charts
helm repo update
helm search repo traefik/traefik
```

---

## 2) Install Traefik (your command)

```bash
helm install traefik traefik/traefik   -n traefik --create-namespace   --set service.type=NodePort   --set ports.web.port=8000   --set ports.web.exposedPort=80   --set ports.web.nodePort=30080   --set ports.websecure.port=8443   --set ports.websecure.exposedPort=443   --set ports.websecure.nodePort=30443   --set ports.traefik.port=8080   --set ports.traefik.exposedPort=8080   --set ports.traefik.nodePort=30090   --set ports.traefik.expose.default=true   --set api.dashboard=true   --set ingressRoute.dashboard.enabled=true
```

---

## 3) What each `--set` does

### Namespace & release
- `helm install traefik traefik/traefik` installs the **traefik** chart and names the Helm release **traefik**.
- `-n traefik --create-namespace` installs into namespace **traefik**, creating it if missing.

### Service type
- `--set service.type=NodePort` exposes Traefik using a Kubernetes **Service** of type **NodePort** (ports open on every node’s IP).

### Ports: `web` (HTTP)
These define how Traefik listens **inside the pod**, what it exposes as a **Service port**, and what **nodePort** Kubernetes opens on nodes.

- `--set ports.web.port=8000`  
  **Container port** Traefik listens on for `web` (HTTP) inside the Traefik pod.
- `--set ports.web.exposedPort=80`  
  **Service port** for `web`. Clients see this as port **80** on the Traefik Service.
- `--set ports.web.nodePort=30080`  
  The **NodePort** opened on each node for HTTP traffic (`:<30080>`).

**Result:** in-pod `:8000` → service `:80` → node `:30080`

### Ports: `websecure` (HTTPS)
- `--set ports.websecure.port=8443`  
  **Container port** Traefik listens on for HTTPS inside the pod.
- `--set ports.websecure.exposedPort=443`  
  **Service port** for HTTPS (443).
- `--set ports.websecure.nodePort=30443`  
  NodePort opened on each node for HTTPS traffic (`:<30443>`).

**Result:** in-pod `:8443` → service `:443` → node `:30443`

### Ports: `traefik` (Dashboard/API)
- `--set ports.traefik.port=8080`  
  **Container port** for Traefik dashboard/API.
- `--set ports.traefik.exposedPort=8080`  
  **Service port** for the dashboard/API.
- `--set ports.traefik.nodePort=30090`  
  NodePort opened on each node for dashboard/API (`:<30090>`).

### Expose behavior for the Traefik entrypoint
- `--set ports.traefik.expose.default=true` ensures the `traefik` (dashboard/API) entrypoint is **exposed by default** via the Service.  
  ⚠️ This makes the dashboard/API reachable—consider restricting access.

### Dashboard & IngressRoute
- `--set api.dashboard=true` enables the **Traefik dashboard** feature.
- `--set ingressRoute.dashboard.enabled=true` creates an **IngressRoute** object for the dashboard (Traefik CRD).

> Note: Exposing the dashboard publicly is not recommended without auth (basic auth, IP allowlist, or VPN).

---

## 4) Verify installation

```bash
kubectl get ns traefik
kubectl get pods -n traefik
kubectl get svc -n traefik
kubectl get ingressroute -n traefik 2>/dev/null || true
```

---

## 5) Access Traefik

### A) Access via NodePort
Pick any node IP and open:

- **HTTP**: `http://<NODE_IP>:30080`
- **HTTPS**: `https://<NODE_IP>:30443`
- **Dashboard**: `http://<NODE_IP>:30090` (or `/dashboard/`)

Find node IPs:
```bash
kubectl get nodes -o wide
```

### B) Port-forward (safer for dashboard)
```bash
kubectl -n traefik port-forward svc/traefik 9000:8080
```
Then open:
- `http://localhost:9000/dashboard/`

---

## 6) Example Ingress (simple)

Deploy a test app:
```bash
kubectl create deploy whoami --image=traefik/whoami
kubectl expose deploy whoami --port 80
```

Ingress manifest (`whoami-ingress.yaml`):
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: whoami
  annotations:
    kubernetes.io/ingress.class: traefik
spec:
  rules:
    - host: whoami.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: whoami
                port:
                  number: 80
```

Apply it:
```bash
kubectl apply -f whoami-ingress.yaml
```

Add to your local `/etc/hosts` (or your DNS):
```
<NODE_IP> whoami.local
```

---

## 7) Upgrade / Uninstall

### Upgrade (keep the same values)
```bash
helm upgrade traefik traefik/traefik -n traefik   --set service.type=NodePort   --set ports.web.port=8000   --set ports.web.exposedPort=80   --set ports.web.nodePort=30080   --set ports.websecure.port=8443   --set ports.websecure.exposedPort=443   --set ports.websecure.nodePort=30443   --set ports.traefik.port=8080   --set ports.traefik.exposedPort=8080   --set ports.traefik.nodePort=30090   --set ports.traefik.expose.default=true   --set api.dashboard=true   --set ingressRoute.dashboard.enabled=true
```

### Uninstall
```bash
helm uninstall traefik -n traefik
# optional: remove namespace
kubectl delete ns traefik
```

---

## Security notes (recommended)

If your cluster is reachable from outside your private network:
- Avoid exposing the dashboard publicly without protection.
- Prefer **port-forward**, VPN, or add **basic auth / IP allowlist** middleware.

---

## Troubleshooting

- **No access to NodePort**: ensure nodes allow inbound traffic on `30080/30443/30090` (firewall / security group).
- **Pods not running**:
  ```bash
  kubectl -n traefik describe pod -l app.kubernetes.io/name=traefik
  kubectl -n traefik logs deploy/traefik
  ```
- **Ingress not routing**: confirm your Ingress class annotation matches Traefik (`kubernetes.io/ingress.class: traefik`).
