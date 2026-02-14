
# Vault Setup Guide for User/Password Authentication with KV Secrets Engine

This guide will walk you through the steps for enabling **user/password authentication**, setting up **KV secrets engine**, storing **database credentials**, creating and assigning **policies**, logging in with the created user, and testing access to the stored credentials.

## Prerequisites

1. Vault is installed and running in your Kubernetes cluster.
2. Access to the Vault web UI or CLI.
3. Kubernetes cluster is configured with Vault enabled.

## Steps

### 1. Enable User/Password Authentication
First, enable the **user/pass** authentication method in Vault.

```bash
vault auth enable userpass
```

### 2. Enable KV Secrets Engine
Enable the **KV secrets engine** to store secrets like database credentials.

```bash
vault secrets enable -path=secret kv
```

This will enable the KV engine under the path `secret/`.

### 3. Create a Policy to Allow Access to Secrets

Create a policy (`my-db-policy.hcl`) that defines which secrets the user can access. In this case, we allow access to `secret/db_credentials`.

```hcl
path "secret/db_credentials" {
  capabilities = ["read"]
}
```

Write the policy to Vault:

```bash
vault policy write my-db-policy my-db-policy.hcl
```

### 4. Store Database Credentials in KV Engine

Now, store the database credentials (e.g., `username` and `password`) in the KV engine.

```bash
vault kv put secret/db_credentials username=my-db-user password=my-db-password
```

### 5. Create a User and Assign the Policy

Now, create a user using the **user/pass** authentication method and assign the `my-db-policy` policy to that user.

```bash
vault write auth/userpass/users/my-db-user password=my-db-password policies=my-db-policy
```

### 6. Log In as the Created User

Use the Vault CLI to log in with the user you just created.

```bash
vault login -method=userpass username=my-db-user password=my-db-password
```

If the login is successful, you will get a token that is associated with the `my-db-policy` policy.

### 7. Test Access to the Stored Database Credentials

Now, test if the user can access the stored database credentials using the Vault CLI.

```bash
vault kv get secret/db_credentials
```

This command should return the `username` and `password` that you stored earlier, as the user `my-db-user` has the `read` permission for this secret.

### Troubleshooting

- If you get a `403 permission denied` error, ensure that:
  - The user has the correct policy (`my-db-policy`) assigned.
  - The policy has `read` permissions for the correct path (`secret/db_credentials`).
  - The secret exists at the specified path.

### Conclusion

This guide showed you how to:
1. Enable user/password authentication in Vault.
2. Enable the KV secrets engine and store database credentials.
3. Create a policy to grant access to the stored secrets.
4. Create a user, assign the policy, and log in.
5. Test the access to the database credentials.

By following these steps, you can manage access to your secrets securely with Vault.
