
# Vault Kubernetes Integration Guide

This guide walks through the steps to configure HashiCorp Vault on Kubernetes to manage secrets for a sample deployment.

## Prerequisites
1. Kubernetes Cluster
2. Vault installed and configured in the Kubernetes environment
3. Vault Kubernetes Auth enabled

## Steps

### 1. Enable Secrets Engine in Vault
First, we need to enable the KV (Key-Value) secrets engine in Vault at the `internal` path.
```bash
kubectl exec -it vault-0 -- /bin/sh
vault secrets enable -path=internal kv-v2
```

### 2. Write Database Credentials to Vault
We store the database credentials in Vault for later injection.
```bash
vault kv put internal/database/config username="db-readonly-username" password="db-secret-password"
```

### 3. Read Data from Vault
You can check the stored data with the following command:
```bash
vault kv get internal/database/config
```

### 4. Enable Kubernetes Authentication
Enable the Kubernetes authentication method for Vault.
```bash
vault auth enable kubernetes
```

### 5. Configure Kubernetes Authentication with Vault
Now configure the Vault Kubernetes authentication method. Make sure to replace the Kubernetes host URL dynamically.
```bash
vault write auth/kubernetes/config kubernetes_host="https://$KUBERNETES_PORT_443_TCP_ADDR:443"
```

### 6. Define Vault Policy
Define a policy for your Kubernetes service account that allows reading the database credentials.
```bash
vault policy write internal-app - <<EOF
path "internal/data/database/config" {
   capabilities = ["read"]
}
EOF
```

### 7. Configure the Kubernetes Role for Vault
This command binds the service account to the policy defined above.
```bash
vault write auth/kubernetes/role/internal-app       bound_service_account_names=internal-app       bound_service_account_namespaces=default       policies=internal-app       ttl=24h
```

### 8. Create the Service Account in Kubernetes
```bash
kubectl create sa internal-app
```

### 9. Define Kubernetes Deployment YAML
Here is the deployment definition, which includes the Vault annotations for secret injection into the pod.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orgchart
  labels:
    app: orgchart
spec:
  selector:
    matchLabels:
      app: orgchart
  replicas: 1
  template:
    metadata:
      labels:
        app: orgchart
      annotations:
        vault.hashicorp.com/agent-inject: 'true'
        vault.hashicorp.com/agent-inject-status: 'update'
        vault.hashicorp.com/role: 'internal-app'
        vault.hashicorp.com/agent-inject-secret-database-config.txt: 'internal/data/database/config'
        vault.hashicorp.com/agent-inject-template-database-config.txt: |
           {{- with secret "internal/data/database/config" -}}
           postgresql://{{ .Data.data.username }}:{{ .Data.data.password }}@postgres:5432/wizard
           {{- end -}}
    spec:
      serviceAccountName: internal-app
      containers:
        - name: orgchart
          image: nginx:alpine
```

### 10. Deploy and Check Pod Status
Deploy the configuration to your Kubernetes cluster:
```bash
kubectl apply -f deployment.yaml
```

Check the pods' status:
```bash
kubectl get pods
```

### 11. Check Vault Agent Logs
You can view the logs from the Vault Agent container in your pod:
```bash
kubectl logs       $(kubectl get pod -l app=orgchart -o jsonpath="{.items[0].metadata.name}")       --container vault-agent
```

### 12. Check Database Configuration File in the Pod
After the Vault Agent injects the secrets into the pod, you can access the database configuration from the file system:
```bash
kubectl exec       $(kubectl get pod -l app=orgchart -o jsonpath="{.items[0].metadata.name}")       --container orgchart -- cat /vault/secrets/database-config.txt
```

### Expected Output
```bash
data: map[password:db-secret-password username:db-readonly-user]
metadata: map[created_time:2019-12-20T18:17:50.930264759Z deletion_time: destroyed:false version:2]
```

---

This guide provides the steps to integrate Vault with Kubernetes for secret management. It includes commands for enabling secrets engines, configuring authentication, deploying with Vault agent injection, and verifying the setup.

