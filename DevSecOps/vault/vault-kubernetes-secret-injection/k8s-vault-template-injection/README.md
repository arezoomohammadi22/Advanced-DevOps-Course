
# Vault Kubernetes Secrets Injection with Template

This guide walks through how to inject secrets into a Kubernetes pod using Vault, and apply a template to structure the secret data.

## Steps

### 1. Apply a Template to Injected Secrets
To structure the format of the injected secrets, a template is used. This helps applications to properly consume the secrets.

#### Display the Patch with Template Definition
Create a YAML file (`patch-inject-secrets-as-template.yaml`) with the following annotations:
```yaml
spec:
   template:
      metadata:
      annotations:
         vault.hashicorp.com/agent-inject: 'true'
         vault.hashicorp.com/agent-inject-status: 'update'
         vault.hashicorp.com/role: 'internal-app'
         vault.hashicorp.com/agent-inject-secret-database-config.txt: 'internal/data/database/config'
         vault.hashicorp.com/agent-inject-template-database-config.txt: |
            {{- with secret "internal/data/database/config" -}}
            postgresql://{{ .Data.data.username }}:{{ .Data.data.password }}@postgres:5432/wizard
            {{- end -}}
```

This patch introduces two new annotations:
1. `agent-inject-status`: Set to `update`, informing the injector to reinject these values.
2. `agent-inject-template-FILEPATH`: Defines the Vault Agent template to apply to the secret's data.

The template formats the `username` and `password` as a PostgreSQL connection string.

#### Apply the Updated Annotations
To apply the updated annotations to the deployment:
```bash
kubectl patch deployment orgchart --patch "$(cat patch-inject-secrets-as-template.yaml)"
```
Output:
```bash
deployment.apps/exampleapp patched
```

### 2. Get All Pods in the Default Namespace
Check the status of the pods in your default namespace:
```bash
kubectl get pods
```
Example output:
```bash
NAME                                    READY   STATUS    RESTARTS   AGE
orgchart-554db4579d-w6565               2/2     Running   0          16s
vault-0                                 1/1     Running   0          126m
vault-agent-injector-5945fb98b5-tpglz   1/1     Running   0          126m
```

### 3. Check the Injected Secrets in the Container
After the pod is redeployed and running, check the injected secrets:
```bash
kubectl exec       $(kubectl get pod -l app=orgchart -o jsonpath="{.items[0].metadata.name}")       -c orgchart -- cat /vault/secrets/database-config.txt
```
Expected output:
```bash
postgresql://db-readonly-user:db-secret-password@postgres:5432/wizard
```

### 4. Applying the Pod Definition with Annotations
Display the pod definition for the payroll application and define the annotations.

#### Payroll Pod Definition
```yaml
apiVersion: v1
kind: Pod
metadata:
name: payroll
labels:
   app: payroll
annotations:
   vault.hashicorp.com/agent-inject: 'true'
   vault.hashicorp.com/role: 'internal-app'
   vault.hashicorp.com/agent-inject-secret-database-config.txt: 'internal/data/database/config'
   vault.hashicorp.com/agent-inject-template-database-config.txt: |
      {{- with secret "internal/data/database/config" -}}
      postgresql://{{ .Data.data.username }}:{{ .Data.data.password }}@postgres:5432/wizard
      {{- end -}}
spec:
serviceAccountName: internal-app
containers:
   - name: payroll
      image: jweissig/app:0.0.1
```

#### Apply the Pod Definition
```bash
kubectl apply --filename pod-payroll.yaml
```
Output:
```bash
pod/payroll created
```

### 5. Get All Pods in the Default Namespace Again
```bash
kubectl get pods
```
Output:
```bash
NAME                                    READY   STATUS    RESTARTS   AGE
orgchart-554db4579d-w6565               2/2     Running   0          29m
payroll                                 2/2     Running   0          12s
vault-0                                 1/1     Running   0          155m
vault-agent-injector-5945fb98b5-tpglz   1/1     Running   0          155m
```

### 6. Check the Injected Secrets in the Payroll Pod
```bash
kubectl exec       payroll       --container payroll -- cat /vault/secrets/database-config.txt
```
Expected output:
```bash
postgresql://db-readonly-user:db-secret-password@postgres:5432/wizard
```

### 7. Secrets Bound to the Service Account
Pods running with a service account that is not defined in the Vault Kubernetes authentication role will not be able to access the secrets.

#### Define the Deployment and Service Account for Website Application
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
name: website
labels:
   app: website
spec:
selector:
   matchLabels:
      app: website
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
         {{- end - }}
      labels:
      app: website
   spec:
      serviceAccountName: website
      containers:
      - name: website
         image: jweissig/app:0.0.1
---
apiVersion: v1
kind: ServiceAccount
metadata:
name: website
```

#### Apply the Deployment and Service Account
```bash
kubectl apply --filename deployment-website.yaml
```
Output:
```bash
deployment.apps/website created
serviceaccount/website created
```

### 8. Get All Pods in the Default Namespace Again
```bash
kubectl get pods
```
Example output:
```bash
NAME                                    READY   STATUS     RESTARTS   AGE
orgchart-554db4579d-w6565               2/2     Running    0          29m
payroll                                 2/2     Running    0          12s
vault-0                                 1/1     Running    0          155m
vault-agent-injector-5945fb98b5-tpglz   1/1     Running    0          155m
website-7fc8b69645-527rf                0/2     Init:0/1   0          76s
```

### 9. Display Logs of the Vault Agent Init Container in the Website Pod
```bash
kubectl logs       $(kubectl get pod -l app=website -o jsonpath="{.items[0].metadata.name}")       --container vault-agent-init
```

#### Expected Error Output:
```bash
[INFO]  auth.handler: authenticating
[ERROR] auth.handler: error authenticating: error="Error making API request.

URL: PUT http://vault.default.svc:8200/v1/auth/kubernetes/login
Code: 403. Errors:

* service account name not authorized" backoff=1.562132589
```

This guide explains how to patch and inject secrets using Vault with Kubernetes. It covers using templates to structure the secret data and also demonstrates service account bindings to ensure proper authorization.
