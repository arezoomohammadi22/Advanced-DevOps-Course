import os
import requests
import kubernetes.client
from kubernetes import config
from urllib3.exceptions import InsecureRequestWarning
import urllib3
import ssl

# Disable SSL warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Disable SSL verification for all requests globally
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Use an insecure SSL context to bypass SSL verification completely
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False  # Disable hostname verification
ssl_context.verify_mode = ssl.CERT_NONE  # Disable certificate verification

# Vault URL and Token are now provided by environment variables in the pod.
vault_url = os.getenv('VAULT_ADDR', 'http://localhost:8200')  # Default to localhost if not set
vault_token = os.getenv('VAULT_TOKEN', '')  # Vault token is pulled from the environment

# Request Kubernetes token from Vault
role = 'my-role'  # Name of your Vault role
namespace = os.getenv('K8S_NAMESPACE', 'default')  # Namespace from environment variables

# Vault API path for getting Kubernetes credentials
url = f"{vault_url}/v1/kubernetes/creds/{role}"

# Headers for request (Authorization using Vault token)
headers = {
    "X-Vault-Token": vault_token
}

# Data to send in request (namespace)
data = {
    "kubernetes_namespace": namespace
}

# Sending POST request to Vault to get Kubernetes token with SSL verification disabled
response = requests.post(url, headers=headers, json=data, verify=False)  # Bypass SSL verification for Vault

# Check response status
if response.status_code == 200:
    # Extract Kubernetes token from response
    k8s_token = response.json()['data']['service_account_token']
    print("Kubernetes Token:", k8s_token)
    
    # Get Kubernetes API server address from environment variables
    k8s_host = os.getenv('KUBERNETES_SERVICE_HOST', 'localhost')  # Default to localhost if not set
    k8s_port = os.getenv('KUBERNETES_SERVICE_PORT', '443')  # Default to port 443 if not set
    k8s_api_url = f'https://{k8s_host}:{k8s_port}'  # Construct the API URL
    
    # Use Kubernetes token to authenticate with SSL verification disabled
    configuration = kubernetes.client.Configuration()
    configuration.host = k8s_api_url
    configuration.api_key = {"authorization": "Bearer " + k8s_token}
    api_client = kubernetes.client.ApiClient(configuration)

    # Disable SSL verification for Kubernetes API using the custom SSL context
    configuration.verify_ssl = False  # Bypass SSL verification for Kubernetes API
    api_client.rest_client.pool_manager.connection_pool_kw['ssl_context'] = ssl_context

    # Request list of pods in the desired namespace
    v1 = kubernetes.client.CoreV1Api(api_client)
    pods = v1.list_namespaced_pod(namespace)

    # Print pod names
    for pod in pods.items:
        print(f"Pod name: {pod.metadata.name}")
else:
    print(f"Failed to get Kubernetes token: {response.status_code}, {response.text}")
