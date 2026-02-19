
# MinIO Client (`mc`) Installation and Setup Guide

This guide will walk you through the steps for installing **MinIO Client (`mc`)**, configuring it to use your MinIO instance on Kubernetes, and setting up the necessary credentials to interact with MinIO via the command line.

## Steps for Installing MinIO Client (`mc`) and Configuring Credentials

### 1. **Install MinIO Client (`mc`)**

MinIO Client (`mc`) is a command-line tool to interact with **MinIO** and compatible object storage services. You can install it on Linux or macOS using the following steps:

#### **Linux/macOS Installation**:

```bash
curl -O https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
mv mc /usr/local/bin/mc
```

#### **Windows Installation**:
Download the executable from [MinIO's website](https://min.io/download#/mc) and add it to your `PATH`.

### 2. **Retrieve the MinIO Credentials**

After deploying MinIO on Kubernetes, the **access key** and **secret key** are stored as **Kubernetes secrets**. To retrieve these credentials, run the following commands:

```bash
kubectl get secret minio -n thanos-test
```

This will list the secrets in the `thanos-test` namespace. Look for the `minio` secret.

To retrieve the **access key** (`rootUser`) and **secret key** (`rootPassword`), run:

```bash
kubectl get secret minio -n thanos-test -o jsonpath="{.data.rootUser}" | base64 --decode
kubectl get secret minio -n thanos-test -o jsonpath="{.data.rootPassword}" | base64 --decode
```

These commands will output the **access key** and **secret key** used for MinIO authentication.

### 3. **Configure MinIO Client (`mc`)**

Once the MinIO client (`mc`) is installed, configure it to use your MinIO instance by setting up an alias with the retrieved credentials.

Run the following command, replacing `<your-k8s-master-ip>` with your Kubernetes master node IP, and using the decoded access key and secret key:

```bash
/usr/local/bin/mc alias set myminio http://10.211.55.50:9000
```

When prompted, enter the **Access Key** and **Secret Key** that you decoded earlier.

```bash
Enter Access Key: <your-access-key>
Enter Secret Key: <your-secret-key>
```

You should see the following output:

```bash
Added `myminio` successfully.
```

This means that the **MinIO client** has been successfully configured to interact with your MinIO instance on Kubernetes.

### 4. **Verify the Connection**

To verify that the `mc` client is working, run:

```bash
mc ls myminio
```

This will list all the buckets in your MinIO instance. If everything is set up correctly, you should see the buckets (if any are created).

### 5. **Working with Buckets and Objects Using `mc`**

Once you’ve set up `mc`, you can create buckets, upload/download objects, and perform other operations. Here are some examples:

- **Create a bucket**:
  ```bash
  mc mb myminio/mybucket
  ```

- **List buckets**:
  ```bash
  mc ls myminio
  ```

- **Upload a file to MinIO**:
  ```bash
  mc cp /path/to/local/file myminio/mybucket/
  ```

- **Download a file from MinIO**:
  ```bash
  mc cp myminio/mybucket/file /path/to/local/destination
  ```

## Conclusion

You have now set up MinIO Client (`mc`), connected it to your MinIO instance on Kubernetes, and learned how to use it for managing objects. You can use the client to interact with your MinIO object storage from the command line.

---

**MinIO Documentation**: https://min.io/docs
