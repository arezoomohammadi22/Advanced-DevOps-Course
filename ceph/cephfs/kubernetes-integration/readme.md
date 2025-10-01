# CephFS CSI on Kubernetes

This guide explains how to deploy and use **CephFS CSI driver** on a Kubernetes cluster using Helm, with full manifests and test instructions.

---

## 1. Pull and Untar the Helm Chart

```bash
helm pull ceph-csi/ceph-csi-cephfs --untar
cd ceph-csi-cephfs
```

---

## 2. Edit `values.yaml`

Update `values.yaml` with your Ceph cluster information:

```yaml
secret:
  create: true
  name: csi-cephfs-secret
  annotations: {}
  userID: admin
  userKey: AQAekNtoMwlLDBAAkLpjT/k0aAQX2AD0iEH5/A==

csiConfig:
  - clusterID: "3a8518be-9dd4-11f0-a471-4e5dca374ac6"
    monitors:
      - "192.168.64.15:6789"
      - "192.168.64.16:6789"
      - "192.168.64.17:6789"
    cephFS:
      fsName: "cephfs"
      pool: "cephfs.cephfs.data"
      subvolumeGroup: "k8s"
      radosNamespace: "csi"
      userID: "client.admin"
      userKey: "AQAekNtoMwlLDBAAkLpjT/k0aAQX2AD0iEH5/A=="
```

> ⚠️ For production, create a dedicated Ceph user (not `client.admin`).

---

## 3. Install CephFS CSI Driver

```bash
helm install ceph-csi-cephfs .   --namespace kube-system   -f values.yaml
```

Verify driver registration:

```bash
kubectl get csidrivers
```
You should see `cephfs.csi.ceph.com`.

---

## 4. Create Subvolume Group on Ceph

On the Ceph cluster:

```bash
ceph fs subvolumegroup create cephfs k8s
```

---

## 5. Create StorageClass

`storageclass.yaml`:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: csi-cephfs-sc
provisioner: cephfs.csi.ceph.com
parameters:
  clusterID: 3a8518be-9dd4-11f0-a471-4e5dca374ac6
  fsName: cephfs
  subvolumeGroup: k8s
  mounter: fuse
  csi.storage.k8s.io/provisioner-secret-name: csi-cephfs-secret
  csi.storage.k8s.io/provisioner-secret-namespace: kube-system
  csi.storage.k8s.io/node-stage-secret-name: csi-cephfs-secret
  csi.storage.k8s.io/node-stage-secret-namespace: kube-system
reclaimPolicy: Delete
allowVolumeExpansion: true
```

Apply:

```bash
kubectl apply -f storageclass.yaml
```

---

## 6. Create PVC

`pvc.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: cephfs-pvc
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 50Gi
  storageClassName: csi-cephfs-sc
```

Apply:

```bash
kubectl apply -f pvc.yaml
```

Check:

```bash
kubectl get pvc cephfs-pvc
```

---

## 7. Create Test Pod

`pod.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: cephfs-test
spec:
  containers:
    - name: app
      image: alpine
      command: ["sh","-c","touch /data/ok && sleep 3600"]
      volumeMounts:
        - mountPath: /data
          name: cephfs-vol
  volumes:
    - name: cephfs-vol
      persistentVolumeClaim:
        claimName: cephfs-pvc
```

Apply:

```bash
kubectl apply -f pod.yaml
```

Check pod status:

```bash
kubectl get pod cephfs-test
```

---

## 8. Verify Mount

Exec into the pod:

```bash
kubectl exec -it cephfs-test -- sh
df -h /data
ls -l /data
echo "hello from cephfs" > /data/hello.txt
cat /data/hello.txt
exit
```

---

## 9. Multi-Pod RWX Test

`pod2.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: cephfs-test2
spec:
  containers:
    - name: app
      image: alpine
      command: ["sh","-c","sleep 3600"]
      volumeMounts:
        - mountPath: /data
          name: cephfs-vol
  volumes:
    - name: cephfs-vol
      persistentVolumeClaim:
        claimName: cephfs-pvc
```

Apply:

```bash
kubectl apply -f pod2.yaml
```

Check shared file:

```bash
kubectl exec -it cephfs-test2 -- cat /data/hello.txt
```

Expected:
```
hello from cephfs
```

---

## 10. Verify from Ceph Side

On Ceph cluster:

```bash
ceph fs subvolume ls cephfs --group_name k8s
```

You should see a subvolume for your PVC (`csi-vol-...`).

---

## 11. Cleanup

```bash
kubectl delete pod cephfs-test cephfs-test2
kubectl delete pvc cephfs-pvc
kubectl delete sc csi-cephfs-sc
helm uninstall ceph-csi-cephfs -n kube-system
```

---

✅ You now have a fully working CephFS CSI setup with RWX volumes on Kubernetes!
