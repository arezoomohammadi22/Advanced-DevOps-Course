
# MinIO Standalone Installation Guide on Kubernetes

This guide will walk you through the steps to install **MinIO** in **standalone mode** on a Kubernetes cluster and how to access its Web UI for managing data.

## Steps for MinIO Installation and Setup

### 1. **Install MinIO using Helm**
   To install MinIO on your Kubernetes cluster using the Helm chart, run the following command:

   ```bash
   helm install minio minio/minio --namespace thanos-test      --set accessKey=myaccesskey,secretKey=mysecretkey,persistence.enabled=false      --set replicas=1      --set mode=standalone
   ```

   This will deploy MinIO in **standalone** mode with one pod, no persistence, and the specified `accessKey` and `secretKey`.

### 2. **Verify MinIO Pod**
   After the Helm installation, check the status of the MinIO pod to ensure it's running correctly:

   ```bash
   kubectl get po -n thanos-test
   ```

   The output should look like this:

   ```
   NAME                                    READY   STATUS    RESTARTS   AGE
   minio-5cf7b5b997-v66cx                  1/1     Running   0          18m
   ```

### 3. **Access MinIO Web UI via Port-Forwarding**
   To access the MinIO Web UI, use port-forwarding:

   ```bash
   kubectl port-forward svc/minio-console 9001:9001 -n thanos-test --address 0.0.0.0
   ```

   This will allow you to access MinIO's console at `http://<your-k8s-master-ip>:9001` in your browser.

### 4. **Login to MinIO Web UI**
   - Open your web browser and navigate to `http://<your-k8s-master-ip>:9001`.
   - Use the **root user** and **root password** you set during the Helm install to log in.

   Example:
   - **Root User**: (Decoded value from the Kubernetes Secret)
   - **Root Password**: (Decoded value from the Kubernetes Secret)

### 5. **Check MinIO Secret**
   You can verify the credentials in Kubernetes by decoding the `rootUser` and `rootPassword` from the `minio` Secret:

   ```bash
   kubectl get secret minio -n thanos-test -o jsonpath="{.data.rootUser}" | base64 --decode
   kubectl get secret minio -n thanos-test -o jsonpath="{.data.rootPassword}" | base64 --decode
   ```

   This will output the **root user** and **root password** used for logging into MinIO.

### 6. **MinIO Console**
   Once logged into the console, you can create buckets and manage your object storage.

```

## Conclusion

You have now set up MinIO in standalone mode, accessed its Web UI, and connected it to your Kubernetes cluster. You can now use MinIO to store data for your applications.

---

**MinIO Documentation**: https://min.io/docs
