
# Vault Kubernetes Secrets Bound to Namespace

This guide walks through how to bind secrets to a specific namespace in Kubernetes using Vault and how to ensure pods in the right namespace can access the secrets.

## Steps

### 1. Create the Offsite Namespace
Start by creating a new namespace named `offsite`:
```bash
kubectl create namespace offsite
```
Output:
```bash
namespace/offsite created
```

### 2. Set the Current Context to the Offsite Namespace
Switch the context to the `offsite` namespace:
```bash
kubectl config set-context --current --namespace offsite
```
Output:
```bash
Context "minikube" modified.
```

### 3. Create a Kubernetes Service Account in the Offsite Namespace
Create the service account `internal-app` in the `offsite` namespace:
```bash
kubectl create sa internal-app
```
Output:
```bash
serviceaccount/internal-app created
```

### 4. Define the Issues Deployment
Display the deployment for the issues application. Create a YAML file (`deployment-issues.yaml`) with the following definition:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
name: issues
labels:
   app: issues
spec:
selector:
   matchLabels:
      app: issues
replicas: 1
template:
   metadata:
      annotations:
      vault.hashicorp.com/agent-inject: 'true'
      vault.hashicorp.com/role: 'internal-app'
      vault.hashicorp.com/agent-inject-secret-database-config.txt: 'internal/data/database/config'
      vault.hashicorp.com/agent-inject-template-database-config.txt: |
         {{- with secret "internal/data/database/config" -}}
         postgresql://{{ .Data.data.username }}:{{ .Data.data.password }}@postgres:5432/wizard
         {{- end -}}
      labels:
      app: issues
   spec:
      serviceAccountName: internal-app
      containers:
      - name: issues
         image: jweissig/app:0.0.1
```

#### Apply the Deployment
```bash
kubectl apply --filename deployment-issues.yaml
```
Output:
```bash
deployment.apps/issues created
```

### 5. Get All Pods in the Offsite Namespace
Check the status of the pods in your `offsite` namespace:
```bash
kubectl get pods
```
Output:
```bash
NAME                      READY   STATUS     RESTARTS   AGE
issues-79d8bf7cdf-dkdlq   0/2     Init:0/1   0          3s
```

### 6. Check Logs of Vault Agent Init in the Issues Pod
Since the issues deployment does not start as expected, check the logs of the `vault-agent-init` container:
```bash
kubectl logs    $(kubectl get pod -l app=issues -o jsonpath="{.items[0].metadata.name}")    --container vault-agent-init
```
The error output will indicate that the namespace is not authorized:
```bash
[INFO]  auth.handler: authenticating
[ERROR] auth.handler: error authenticating: error="Error making API request.

URL: PUT http://vault.default.svc:8200/v1/auth/kubernetes/login
Code: 500. Errors:

* namespace not authorized" backoff=1.9882590740000001
```

### 7. Create the Vault Authentication Role for the Offsite Namespace
Start an interactive shell session on the `vault-0` pod in the default namespace:
```bash
kubectl exec --namespace default -it vault-0 -- /bin/sh
```

Create the Vault authentication role for the `offsite` namespace:
```bash
vault write auth/kubernetes/role/offsite-app    bound_service_account_names=internal-app    bound_service_account_namespaces=offsite    policies=internal-app    ttl=24h
```
Output:
```bash
Success! Data written to: auth/kubernetes/role/offsite-app
```

Exit the `vault-0` pod:
```bash
exit
```

### 8. Patch the Issues Deployment
Define the patch for the issues deployment (`patch-issues.yaml`) to set the role to `offsite-app`:
```yaml
spec:
template:
   metadata:
      annotations:
      vault.hashicorp.com/agent-inject: 'true'
      vault.hashicorp.com/agent-inject-status: 'update'
      vault.hashicorp.com/role: 'offsite-app'
      vault.hashicorp.com/agent-inject-secret-database-config.txt: 'internal/data/database/config'
      vault.hashicorp.com/agent-inject-template-database-config.txt: |
         {{- with secret "internal/data/database/config" -}}
         postgresql://{{ .Data.data.username }}:{{ .Data.data.password }}@postgres:5432/wizard
         {{- end -}}
```

#### Apply the Patch
```bash
kubectl patch deployment issues --patch "$(cat patch-issues.yaml)"
```
Output:
```bash
deployment.apps/issues patched
```

### 9. Get All Pods in the Offsite Namespace Again
```bash
kubectl get pods
```
Output:
```bash
NAME                      READY   STATUS    RESTARTS   AGE
issues-7fd66f98f6-ffzh7   2/2     Running   0          94s
```

### 10. Check the Injected Secrets in the Issues Pod
```bash
kubectl exec    $(kubectl get pod -l app=issues -o jsonpath="{.items[0].metadata.name}")    --container issues -- cat /vault/secrets/database-config.txt
```
Expected output:
```bash
postgresql://db-readonly-user:db-secret-password@postgres:5432/wizard
```

---

This guide explains how to bind Kubernetes namespaces to Vault authentication roles, allowing pods in the `offsite` namespace to access secrets.
