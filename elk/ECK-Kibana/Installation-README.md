# Kibana on Kubernetes with ECK (Elastic Cloud on Kubernetes)

This guide installs **Kibana using ECK** and keeps it exposed as a **ClusterIP** service inside the cluster.  
(Optional) It also shows how to expose Kibana externally via **Traefik (NodePort)** with **HTTPS**, based on our setup.

---

## Prerequisites

- A running Kubernetes cluster
- **ECK operator installed**
- An Elasticsearch cluster deployed via ECK (example name: `es-logging`)
- `kubectl` access to the cluster
- Access to your private registry (example: `docker.arvancloud.ir`)

---

## 1) Verify Elasticsearch exists

```bash
kubectl get elasticsearch -A
```

---

## 2) Create imagePullSecret (if registry is private)

```bash
kubectl create secret docker-registry arvan-regcred \
  --docker-server=docker.arvancloud.ir \
  --docker-username='<USERNAME>' \
  --docker-password='<PASSWORD>' \
  --docker-email='<EMAIL>' \
  -n default
```

---

## 3) Kibana manifest (ECK)

```yaml
apiVersion: kibana.k8s.elastic.co/v1
kind: Kibana
metadata:
  name: kibana-logging
  namespace: default
spec:
  version: 8.15.3
  image: docker.arvancloud.ir/kibana:8.15.3
  count: 1

  elasticsearchRef:
    name: es-logging

  http:
    service:
      spec:
        type: ClusterIP

  podTemplate:
    spec:
      imagePullSecrets:
        - name: arvan-regcred
```

Apply:
```bash
kubectl apply -f kibana.yaml
```

---

## 4) Check status

```bash
kubectl get kibana -n default
kubectl get pods -n default | grep kibana
kubectl get svc -n default | grep kibana
```

---

## 5) Access Kibana (internal)

```bash
kubectl port-forward -n default svc/kibana-logging-kb-http 5601:5601
```

Open:
http://127.0.0.1:5601

---

## 6) Optional: Expose via Traefik (HTTPS NodePort)

See Traefik IngressRoute + Middleware + ServersTransport configuration as discussed.

---

## Notes

- Keep Kibana as ClusterIP and expose via Traefik
- Use HTTPS for login
- Use real TLS certs for production
