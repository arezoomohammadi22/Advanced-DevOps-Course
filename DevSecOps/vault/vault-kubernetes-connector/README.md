
# Kubernetes Vault Integration

This project demonstrates the integration of Vault with Kubernetes for managing secrets and service account tokens. The following components are configured:

## Vault Secret

A Kubernetes Secret is used to store the Vault token for authentication.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: vault-secrets
  namespace: sample
type: Opaque
data:
  vault-token: aHZzLlo1MjdsZEhkTWZQcXVaczdZcm51SHkzMQ== # Replace this with the base64-encoded Vault token
```

## Python Application (`myapp.py`)

This Python script connects to Vault and Kubernetes to retrieve the Kubernetes service account token using the Vault Kubernetes authentication method. It bypasses SSL verification using a custom SSL context.

### Python Dependencies:
- `requests`
- `kubernetes`
- `urllib3`

### Configuration:
- Vault URL: Configured from the environment (`VAULT_ADDR`).
- Vault Token: Configured from the environment (`VAULT_TOKEN`).
- Kubernetes Namespace: Configured from the environment (`K8S_NAMESPACE`).
- Kubernetes API URL: Constructed using `KUBERNETES_SERVICE_HOST` and `KUBERNETES_SERVICE_PORT`.

```python
import os
import requests
import kubernetes.client
from kubernetes import config
from urllib3.exceptions import InsecureRequestWarning
import urllib3
import ssl

# Disable SSL warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# SSL context to bypass certificate verification
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Vault URL and Token
vault_url = os.getenv('VAULT_ADDR', 'http://localhost:8200')
vault_token = os.getenv('VAULT_TOKEN', '')

# Request Kubernetes token from Vault
role = 'my-role'
namespace = os.getenv('K8S_NAMESPACE', 'default')
url = f"{vault_url}/v1/kubernetes/creds/{role}"
headers = {
    "X-Vault-Token": vault_token
}
data = {
    "kubernetes_namespace": namespace
}
response = requests.post(url, headers=headers, json=data, verify=False)

if response.status_code == 200:
    k8s_token = response.json()['data']['service_account_token']
    print("Kubernetes Token:", k8s_token)
else:
    print(f"Failed to get Kubernetes token: {response.status_code}, {response.text}")
```

## Kubernetes Deployment (`deploy.yaml`)

The deployment configuration for the Python app, including Vault token injection and Kubernetes service account.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-python-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-python-app
  template:
    metadata:
      labels:
        app: my-python-app
    spec:
      containers:
        - name: my-python-app
          image: my-python-app:v1
          imagePullPolicy: IfNotPresent
          env:
            - name: VAULT_ADDR
              value: "http://10.211.55.50:8200"
            - name: VAULT_TOKEN
              valueFrom:
                secretKeyRef:
                  name: vault-secrets
                  key: vault-token
            - name: KUBERNETES_API_URL
              value: "https://kubernetes.default.svc"
            - name: K8S_NAMESPACE
              value: "sample"
      serviceAccountName: test-service-account-with-generated-token
```

## Running the Application

To run the application, ensure you have the following:

1. Kubernetes cluster with a running Vault instance.
2. Configure the `vault-secrets` Secret in the `sample` namespace.
3. Deploy the application using the `deploy.yaml` file.

```bash
kubectl apply -f deploy.yaml
```

After deployment, the application will retrieve the Kubernetes service account token from Vault and print the token.
