# Ceph-CSI RBD on Kubernetes

This repository documents the steps to deploy and test **Ceph-CSI RBD** integration with an external Ceph cluster on Kubernetes.

---

## 🚀 Prerequisites
- A running Ceph cluster (installed via `cephadm` or other method).
- A Kubernetes cluster with `kubectl` and `helm` configured.
- Ceph client admin key available.

---

## 🔹 Step 1: Install Ceph-CSI using Helm

```bash
helm repo add ceph-csi https://ceph.github.io/csi-charts
helm repo update
helm install ceph-csi-rbd ceph-csi/ceph-csi-rbd -n kube-system
```

---

## 🔹 Step 2: Get Ceph Cluster Info

On Ceph admin node:

```bash
ceph fsid
ceph auth get-key client.admin
```

Example:
```
FSID: 21efc9b2-97bb-11f0-b9c8-0d048039805b
Key:  AQC0VNFoEEH9IBAAiBnxsxRqrwO9UZpf6/K8jA==
```

---

## 🔹 Step 3: Create Secret in Kubernetes

⚠️ Use **admin** (not `client.admin`) as userID.

```bash
kubectl -n kube-system create secret generic csi-rbd-secret   --from-literal=userID=admin   --from-literal=userKey='AQC0VNFoEEH9IBAAiBnxsxRqrwO9UZpf6/K8jA=='
```

---

## 🔹 Step 4: Create StorageClass

`storageclass.yaml`:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ceph-rbd
provisioner: rbd.csi.ceph.com
parameters:
  clusterID: 21efc9b2-97bb-11f0-b9c8-0d048039805b
  pool: sananet-pool
  imageFeatures: layering
  csi.storage.k8s.io/provisioner-secret-name: csi-rbd-secret
  csi.storage.k8s.io/provisioner-secret-namespace: kube-system
  csi.storage.k8s.io/node-stage-secret-name: csi-rbd-secret
  csi.storage.k8s.io/node-stage-secret-namespace: kube-system
reclaimPolicy: Delete
allowVolumeExpansion: true
```

Apply:
```bash
kubectl apply -f storageclass.yaml
```

---

## 🔹 Step 5: Test with PVC

`pvc-test.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: rbd-pvc-test
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: ceph-rbd
```

Apply and check:
```bash
kubectl apply -f pvc-test.yaml
kubectl get pvc
```

---

## 🔹 Step 6: Test Pod with PVC

`pod-test.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: rbd-test-pod
spec:
  containers:
  - name: app
    image: busybox
    command: ["sleep", "3600"]
    volumeMounts:
    - mountPath: /mnt/rbd
      name: test-vol
  volumes:
  - name: test-vol
    persistentVolumeClaim:
      claimName: rbd-pvc-test
```

Test:
```bash
kubectl apply -f pod-test.yaml
kubectl exec -it rbd-test-pod -- sh
echo "hello ceph" > /mnt/rbd/test.txt
cat /mnt/rbd/test.txt
```

---

## ✅ Verification

On Ceph side:
```bash
rbd ls sananet-pool
```

You should see an image created by CSI.  

On Kubernetes side:
```bash
kubectl get pvc
kubectl get pods
```

PVC should be **Bound** and Pod should be **Running**.

---

## ⚠️ Notes
- Always use `admin` instead of `client.admin` in Kubernetes Secrets.
- Best practice: create a dedicated CephX user (`client.csi-rbd`) with limited caps.
- For production, enable TLS and consider restricting pools per namespace.

---

## 📝 License
Apache-2.0, same as [Ceph-CSI](https://github.com/ceph/ceph-csi).
