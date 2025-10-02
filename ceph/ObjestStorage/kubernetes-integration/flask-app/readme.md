# Flask S3 Sample App with Ceph RGW

This project demonstrates how to deploy a **Flask application** on Kubernetes that stores and retrieves objects from a **Ceph RGW (S3-compatible object storage)**.

---

## 🚀 Prerequisites
- A running Kubernetes cluster
- A running Ceph cluster with RGW enabled
- `kubectl` configured
- `s3cmd` installed on Ceph node or admin node
- Access and secret keys for a Ceph RGW user

---

## 🔑 Step 1: Create RGW User and Bucket

### Create User (if not already)
```bash
radosgw-admin user create --uid=k8s-user --display-name="K8s User"
```

This command outputs `access_key` and `secret_key`.

### Configure s3cmd
```bash
s3cmd --configure
```
Enter:
```
Access Key: <ACCESS_KEY>
Secret Key: <SECRET_KEY>
Default Region: us-east-1
S3 Endpoint: http://192.168.64.15:8080
Use HTTPS: False
```

### Create Bucket
```bash
s3cmd mb s3://my-bucket
s3cmd ls
```

✅ Ensure the bucket exists before deploying the app.

---

## 🔐 Step 2: Create Kubernetes Secret

Save Ceph RGW credentials and bucket info in Kubernetes:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ceph-s3-secret
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: "<ACCESS_KEY>"
  AWS_SECRET_ACCESS_KEY: "<SECRET_KEY>"
  AWS_BUCKET: "my-bucket"
  AWS_REGION: "us-east-1"
  AWS_ENDPOINT: "http://192.168.64.15:8080"
```

Apply:
```bash
kubectl apply -f secret.yaml
```

---

## 📦 Step 3: Build and Load Flask App Image

Build the Flask app image and push it into your cluster:

```bash
# Build locally
docker build -t flask-s3:latest .

# Save and load into containerd (if using containerd runtime)
docker save flask-s3:latest | ctr -n=k8s.io images import -
```

---

## 🛠 Step 4: Deploy Flask App on Kubernetes

Deployment manifest (`deployment.yaml`):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flask-s3
spec:
  replicas: 1
  selector:
    matchLabels:
      app: flask-s3
  template:
    metadata:
      labels:
        app: flask-s3
    spec:
      nodeName: k8s-master   # adjust to your master node name
      tolerations:
      - key: "node-role.kubernetes.io/master"
        operator: "Exists"
        effect: "NoSchedule"
      - key: "node-role.kubernetes.io/control-plane"
        operator: "Exists"
        effect: "NoSchedule"
      containers:
      - name: flask-s3
        image: flask-s3:latest
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 5000
        envFrom:
        - secretRef:
            name: ceph-s3-secret
```

Service manifest (`service.yaml`):

```yaml
apiVersion: v1
kind: Service
metadata:
  name: flask-s3
spec:
  type: NodePort
  selector:
    app: flask-s3
  ports:
  - port: 80
    targetPort: 5000
    nodePort: 30080
```

Apply:
```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

---

## 🔍 Step 5: Test the App

Port forward or use NodePort to access the app.

### Upload a file
```bash
curl -F "file=@/etc/hosts" http://<NODE_IP>:30080/upload
```

### List files
```bash
curl http://<NODE_IP>:30080/list
```

---

## 🧹 Cleanup
```bash
kubectl delete -f deployment.yaml
kubectl delete -f service.yaml
kubectl delete secret ceph-s3-secret
```

---

## ✅ Summary
- Bucket created with `s3cmd` on Ceph RGW
- Flask app deployed on Kubernetes
- Files uploaded via Flask → stored in Ceph RGW bucket
- Files listed and retrieved through S3 API
