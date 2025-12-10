# Elasticsearch on Kubernetes using ECK (Elastic Cloud on Kubernetes)

This guide explains how to deploy a production-grade Elasticsearch cluster on a Kubernetes
cluster using **ECK (Elastic Cloud on Kubernetes)**. It includes installation steps, cluster
creation, custom image usage, scaling, upgrades, and validation workflow.

---

## 📌 Overview

ECK is the official Kubernetes Operator for running the Elastic Stack (Elasticsearch, Kibana,
APM, Beats, Enterprise Search) on Kubernetes.  
It automates:

- Elasticsearch cluster creation  
- Scaling & self-healing  
- Rolling upgrades  
- TLS & user management  
- Storage orchestration  
- Health monitoring  
- Image overrides for private registries  

---

## 🏗 Architecture

ECK consists of two core components:

### **1. CRDs (Custom Resource Definitions)**
Extend Kubernetes with new object types:

- `Elasticsearch`
- `Kibana`
- `ApmServer`
- `Beat`, `Agent`, etc.

### **2. Elastic Operator**
A controller that continuously reconciles desired state vs actual state:

- Creates StatefulSets, PVCs, Services  
- Generates TLS certificates  
- Creates security credentials  
- Ensures cluster health  
- Manages upgrades  

---

## 🚀 Installation

### **1. Install CRDs**

```bash
kubectl apply -f https://download.elastic.co/downloads/eck/2.13.0/crds.yaml
```

### **2. Install the Operator**

```bash
kubectl apply -f https://download.elastic.co/downloads/eck/2.13.0/operator.yaml
```

Verify:

```bash
kubectl -n elastic-system get pods
```

Operator should be `Running`.

---

## 📦 Deploying Elasticsearch Cluster

Create `es-cluster.yaml`:

```yaml
apiVersion: elasticsearch.k8s.elastic.co/v1
kind: Elasticsearch
metadata:
  name: es-logging
spec:
  version: 8.15.3
  image: docker.arvancloud.ir/elasticsearch:8.15.3
  nodeSets:
    - name: default
      count: 3
      config:
        node.store.allow_mmap: false
      volumeClaimTemplates:
        - metadata:
            name: elasticsearch-data
          spec:
            accessModes: ["ReadWriteOnce"]
            resources:
              requests:
                storage: 50Gi
            storageClassName: nfs-client
```

Apply:

```bash
kubectl apply -f es-cluster.yaml
```

---

## 🔐 Security & Credentials

ECK automatically generates:

- Cluster CA + node certificates  
- HTTP TLS certificates  
- Transport TLS certificates  
- `elastic` superuser password  

Retrieve password:

```bash
kubectl get secret es-logging-es-elastic-user -o go-template='{{.data.elastic | base64decode}}'
```

---

## 🌐 Accessing Elasticsearch

Port-forward:

```bash
kubectl port-forward svc/es-logging-es-http 9200
```

Test:

```bash
curl -k -u elastic:<password> https://localhost:9200
curl -k -u elastic:<password> https://localhost:9200/_cluster/health?pretty
```

---

## 🏗 Scaling the Cluster

Update your CR:

```yaml
spec:
  nodeSets:
    - name: default
      count: 5
```

Apply:

```bash
kubectl apply -f es-cluster.yaml
```

ECK will:

- Add new nodes  
- Rebalance shards  
- Ensure cluster health  

---

## 🔄 Rolling Upgrades

To upgrade Elasticsearch:

```yaml
spec:
  version: 8.15.4
  image: docker.arvancloud.ir/elasticsearch:8.15.4
```

Apply and ECK will perform:

- Safe node draining  
- One-by-one rolling restart  
- Cluster stabilization  

---

## 🧪 Monitoring Cluster Health

### Kubernetes:

```bash
kubectl get elasticsearch
kubectl describe elasticsearch es-logging
kubectl get pods -l elasticsearch.k8s.elastic.co/cluster-name=es-logging
```

### REST API:

```bash
curl -k -u elastic:<password> https://localhost:9200/_cluster/health?pretty
```

Health states:

- **green** → all primary & replica shards active  
- **yellow** → replica shards missing  
- **red** → primary shards missing  

---

## 🏁 Full Deployment Workflow

1. Install ECK CRDs  
2. Install ECK Operator  
3. Deploy `es-logging` cluster CR  
4. Verify StatefulSets, pods, PVCs  
5. Retrieve `elastic` credentials  
6. Validate TLS/HTTP access  
7. Scale or upgrade as needed  
8. Monitor Kubernetes + Elasticsearch APIs  

---

## 📚 Additional Notes

### Custom Private Registry
ECK allows overriding registry per cluster:

```yaml
spec:
  image: docker.arvancloud.ir/elasticsearch:8.15.3
```

Or globally with operator arg:

```
--container-registry=my.registry
```

### Storage
Use `StatefulSet` PVCs for persistent elasticsearch data.  
Storage remains even if cluster is deleted unless removed manually.

---

## ✔ Summary

With ECK, Elasticsearch becomes:

- Declarative  
- Automated  
- Secure  
- Highly available  
- Easy to scale  
- Easy to maintain  

## 📄 License

Apache 2.0 (same as Elastic OSS components)
