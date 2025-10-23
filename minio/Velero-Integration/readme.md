# 🧰 Velero + MinIO Backup Setup Guide

This guide explains how to install **Velero** on a Kubernetes cluster and configure it to use **MinIO** as an S3-compatible backup backend.

---

## 🧩 Prerequisites

- A running Kubernetes cluster (`kubectl` access)
- External MinIO server (reachable from cluster)
  - Example endpoint: `http://10.211.55.63:9000`
  - A bucket created for Velero (e.g. `velero-backups`)
  - Access key and secret key for MinIO
- Installed Velero CLI on your admin machine

Verify Velero CLI:
```bash
velero version
```

---

## ⚙️ 1. Create a MinIO Bucket

On any machine with `mc` (MinIO Client):
```bash
mc alias set myminio http://10.211.55.63:9000 <ACCESS_KEY> <SECRET_KEY>
mc mb myminio/velero-backups || true
```

---

## 🔑 2. Create Velero Credentials File

Create a file called `credentials-velero`:
```ini
[default]
aws_access_key_id = <ACCESS_KEY>
aws_secret_access_key = <SECRET_KEY>
```

---

## 🚀 3. Install Velero with MinIO Backend

```bash
kubectl create namespace velero

velero install   --namespace velero   --provider aws   --plugins velero/velero-plugin-for-aws:v1.11.0   --bucket velero-backups   --secret-file ./credentials-velero   --use-volume-snapshots=false   --backup-location-config region=minio,s3ForcePathStyle="true",s3Url=http://10.211.55.63:9000
```

### 🔍 Verify Installation
```bash
kubectl get pods -n velero
velero backup-location get
```

The location should show **Available**.

---

## 🧪 4. Test Backup & Restore

### 4.1 Create Sample App
```bash
kubectl create ns demo
kubectl -n demo create deployment nginx --image=nginx:stable
kubectl -n demo expose deployment nginx --port=80 --target-port=80
kubectl -n demo get all
```

### 4.2 Create a Backup
```bash
velero backup create demo-backup --include-namespaces demo
velero backup describe demo-backup --details
```

Check MinIO bucket: `mc ls myminio/velero-backups`

### 4.3 Restore
```bash
kubectl delete ns demo
velero restore create --from-backup demo-backup
kubectl get ns
kubectl -n demo get all
```

---

## 🕒 5. Optional – Schedule Automatic Backups
```bash
velero schedule create nightly   --schedule="0 2 * * *"   --ttl 168h
velero schedule get
```

---

## 🧠 Notes

| Feature | Description |
|----------|-------------|
| `--use-volume-snapshots=false` | Disables CSI snapshots (manifest-level only) |
| `s3ForcePathStyle="true"` | Required for MinIO and other S3-compatible stores |
| `s3Url=http://<MINIO_IP>:9000` | Your MinIO endpoint |
| `velero uninstall` | Removes Velero from the cluster |

---

## ✅ Verify in MinIO

Use `mc` or MinIO console to confirm backup files are written to your bucket:
```bash
mc ls myminio/velero-backups
```

You should see directories like:
```
backups/demo-backup/
restores/demo-backup/
```

---

## 📚 References
- [Velero Official Docs](https://velero.io/docs/)
- [MinIO + Velero Integration Guide](https://docs.min.io/docs/velero-with-minio.html)
- [Velero AWS Plugin](https://github.com/vmware-tanzu/velero-plugin-for-aws)

---

**Author:** Generated with ❤️ for a self-hosted MinIO + Velero environment.
