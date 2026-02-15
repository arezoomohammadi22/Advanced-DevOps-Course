
# Vault Kubernetes Integration Setup

This repository contains Kubernetes manifests and commands for setting up Vault's Kubernetes integration to create dynamic service account tokens and use them for accessing Kubernetes resources.

## Overview

This setup enables you to integrate Vault with your Kubernetes cluster for the dynamic creation and management of service account tokens. The tokens are associated with specific Kubernetes service accounts and can be used by applications to access Kubernetes resources securely.

### Files Included:
- `clusterrole.yaml`: ClusterRole manifest with permissions to manage service accounts, roles, and more.
- `clusterrolebinding.yaml`: ClusterRoleBinding manifest for binding the ClusterRole to the Vault service account.
- `sa.yaml`: ServiceAccount and associated Role/RoleBinding manifests for the application.
- Vault commands for enabling Kubernetes secrets engine, creating roles, and writing credentials.

## Prerequisites

- Kubernetes cluster
- Vault installed on your cluster
- kubectl installed and configured to interact with your cluster

## Vault Setup

1. **Enable the Kubernetes Secrets Engine in Vault:**

   Run the following command to enable Kubernetes secrets engine on Vault:

   ```bash
   vault secrets enable kubernetes
   ```

2. **Configure the Kubernetes Authentication Method:**

   Create a Kubernetes configuration file for Vault:

   ```bash
   vault write -f kubernetes/config
   ```

   This command allows Vault to authenticate with your Kubernetes cluster.

3. **Create a Vault Role for Service Account Tokens:**

   Create a Vault role that defines the allowed Kubernetes namespaces and service account name:

   ```bash
   vault write kubernetes/roles/my-role      allowed_kubernetes_namespaces="*"      service_account_name="test-service-account-with-generated-token"      token_default_ttl="10m"
   ```

   This role specifies that the service account `test-service-account-with-generated-token` in any namespace is allowed to request tokens with a TTL of 10 minutes.

4. **Create a Service Account and Role in Kubernetes:**

   The following Kubernetes manifests create a service account, a role, and a role binding to allow it to list pods in the `test` namespace.

   ### `sa.yaml`:

   ```yaml
   apiVersion: v1
   kind: ServiceAccount
   metadata:
     name: test-service-account-with-generated-token
     namespace: test
   ---
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: test-role-list-pods
     namespace: test
   rules:
   - apiGroups: [""]
     resources: ["pods"]
     verbs: ["list"]
   ---
   apiVersion: rbac.authorization.k8s.io/v1
   kind: RoleBinding
   metadata:
     name: test-role-abilities
     namespace: test
   roleRef:
     apiGroup: rbac.authorization.k8s.io
     kind: Role
     name: test-role-list-pods
   subjects:
   - kind: ServiceAccount
     name: test-service-account-with-generated-token
     namespace: test
   ```

   Apply the manifests:

   ```bash
   kubectl apply -f sa.yaml
   ```

5. **Create a ClusterRole and ClusterRoleBinding:**

   The following manifests create a `ClusterRole` and a `ClusterRoleBinding` for Vault to allow it to interact with service accounts and roles.

   ### `clusterrole.yaml`:

   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: ClusterRole
   metadata:
     name: k8s-full-secrets-abilities-with-labels
   rules:
   - apiGroups: [""]
     resources: ["namespaces"]
     verbs: ["get"]
   - apiGroups: [""]
     resources: ["serviceaccounts", "serviceaccounts/token"]
     verbs: ["create", "update", "delete"]
   - apiGroups: ["rbac.authorization.k8s.io"]
     resources: ["rolebindings", "clusterrolebindings"]
     verbs: ["create", "update", "delete"]
   - apiGroups: ["rbac.authorization.k8s.io"]
     resources: ["roles", "clusterroles"]
     verbs: ["bind", "escalate", "create", "update", "delete"]
   ```

   ### `clusterrolebinding.yaml`:

   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: ClusterRoleBinding
   metadata:
     name: vault-token-creator-binding
   roleRef:
     apiGroup: rbac.authorization.k8s.io
     kind: ClusterRole
     name: k8s-full-secrets-abilities-with-labels
   subjects:
   - kind: ServiceAccount
     name: vault
     namespace: default
   ```

   Apply the manifests:

   ```bash
   kubectl apply -f clusterrole.yaml
   kubectl apply -f clusterrolebinding.yaml
   ```

## Generate Kubernetes Service Account Token

1. **Request a Token from Vault:**

   Run the following command to generate a service account token using Vault:

   ```bash
   vault write kubernetes/creds/my-role kubernetes_namespace=test
   ```

   Vault will return a service account token, which can be used to authenticate against the Kubernetes API.

   Example output:

   ```bash
   Key                        Value
   ---                        -----
   lease_id                   kubernetes/creds/my-role/31d771a6-...
   lease_duration             10m0s
   lease_renewable            false
   service_account_name       test-service-account-with-generated-token
   service_account_namespace  test
   service_account_token      eyJHbGci0iJSUzI1NiIsImtpZCI6ImlrUEE...
   ```

2. **Use the Token to Make Kubernetes API Requests:**

   Once the token is generated, you can use it to make API requests to Kubernetes. For example, to list pods in the `test` namespace:

   ```bash
   curl -sk $(kubectl config view --minify -o 'jsonpath={.clusters[].cluster.server}')/api/v1/namespaces/test/pods      --header "Authorization: Bearer eyJHbGci0iJSUzI1Ni..."
   ```

   This will return the list of pods in the `test` namespace.

3. **Verify Token Expiry:**

   When the token expires, you will receive an error if you try to use it again. Verify the token expiry by re-running the above `curl` command after the TTL has passed.

---

## Conclusion

With this setup, you can dynamically manage Kubernetes service account tokens through Vault. These tokens are associated with specific roles, permissions, and expiration times, ensuring a secure and automated mechanism for your application to access Kubernetes resources.
