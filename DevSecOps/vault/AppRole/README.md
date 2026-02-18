
# Vault Configuration Guide: AppRole, Policies, and Role Setup

This document explains how to configure **Vault AppRole** authentication, create and define **policies**, and grant access to key-value paths within **Vault**. It covers the steps to set up **AppRole** authentication, create **Vault policies**, and configure access control to secrets stored in Vault.

## Table of Contents

1. [Vault AppRole Authentication](#vault-approle-authentication)
2. [Create Vault Role and Policies](#create-vault-role-and-policies)
3. [Grant Access to Secret Paths](#grant-access-to-secret-paths)
4. [Policy Examples](#policy-examples)
5. [Enable KV and Set Secrets](#enable-kv-and-set-secrets)

---

## Vault AppRole Authentication

### 1. Enable AppRole Authentication

The first step is to enable **AppRole** authentication in Vault. AppRole allows machines or applications to authenticate securely with Vault.

Run the following command to enable **AppRole** authentication:

```bash
vault auth enable approle
```

This will enable the AppRole authentication method at the `approle/` endpoint in Vault.

### 2. Create Vault Role

Once AppRole authentication is enabled, you need to create a **role** that defines the permissions and TTL settings for generated tokens. Roles are used to group policies and define access permissions for applications or machines.

Run the following command to create an **AppRole**:

```bash
vault write auth/approle/role/gitlab-role   policies="gitlab-secrets-policy"   token_ttl=1h   token_max_ttl=4h
```

Where:
- `gitlab-role`: the name of the role.
- `gitlab-secrets-policy`: the policy that grants permissions for the secrets.
- `token_ttl`: time-to-live for the token generated for the role (e.g., 1 hour).
- `token_max_ttl`: maximum allowed TTL for the generated token (e.g., 4 hours).

### 3. Retrieve Role ID and Secret ID

Once the role is created, you need to retrieve the **Role ID** and generate the **Secret ID** for use in authentication.

#### Get Role ID:

Run the following command to retrieve the **Role ID** for the `gitlab-role`:

```bash
vault read auth/approle/role/gitlab-role/role-id
```

Example output:

```bash
Key        Value
---        -----
role_id    69f80a43-f774-2b2a-b96e-7402fe4b37f7
```

#### Generate Secret ID:

Run the following command to generate the **Secret ID** for the role:

```bash
vault write -f auth/approle/role/gitlab-role/secret-id
```

Example output:

```bash
Key                   Value
---                   -----
secret_id             9e9accbe-e9c5-0800-c45e-c9282336783c
secret_id_accessor    a1a303be-5a7d-bcc8-0bb8-48d1449f9ce1
secret_id_num_uses    0
secret_id_ttl         1h
```

- Store the `role_id` and `secret_id` for later use in your GitLab CI/CD pipeline.

---

## Create Vault Role and Policies

Once you’ve enabled AppRole authentication and created your role, the next step is to create and configure **policies** that define what secrets the role can access.

### 1. Create Vault Policy

A **policy** in Vault defines the **capabilities** (such as `read`, `list`, `create`, etc.) on specific paths in the Vault storage.

Create a **policy** for the `gitlab-role` role by defining access to certain key-value paths in Vault.

#### Example Policy: `gitlab-secrets-policy.hcl`

```hcl
# For KV version 2 (Vault Key-Value secrets engine v2)
path "secret/data/gitlab/*" {
  capabilities = ["read", "list"]
}

# For KV version 1 (Vault Key-Value secrets engine v1)
path "secret/gitlab/*" {
  capabilities = ["read"]
}
```

In this policy:
- **For KV v2**: The path `secret/data/gitlab/*` allows **read** and **list** access to all secrets under that path.
- **For KV v1**: The path `secret/gitlab/*` allows **read** access to all secrets under that path.

#### Apply the Policy to Vault

Save the policy into a file named `gitlab-secrets-policy.hcl`, and then apply it to Vault using the following command:

```bash
vault policy write gitlab-secrets-policy gitlab-secrets-policy.hcl
```

### 2. Assign Policies to the Role

You can assign multiple policies to the **role** when creating it, as shown in the previous example where we assigned `gitlab-secrets-policy` to the `gitlab-role` role. This gives the role the permissions defined in the policy.

---

## Grant Access to Secret Paths

Vault uses **policies** to control access to **secrets**. You can define **key-value** paths and specify what actions a role can perform (e.g., `read`, `create`, `list`).

### 1. Define Secret Paths

- **KV v1 Example**: To allow read access to the `gitlab` secrets in **KV version 1**, the path would be `secret/gitlab/*`.

- **KV v2 Example**: For **KV version 2**, use the path `secret/data/gitlab/*`.

### 2. Configure Access in the Policy

In the **policy** you defined (`gitlab-secrets-policy`), you can configure the **capabilities** for specific paths. For example:

- **For KV version 1**:

  ```hcl
  path "secret/gitlab/*" {
    capabilities = ["read"]
  }
  ```

- **For KV version 2**:

  ```hcl
  path "secret/data/gitlab/*" {
    capabilities = ["read", "list"]
  }
  ```

The **capabilities** available are:
- **read**: Allows reading secrets.
- **list**: Allows listing keys.
- **create**: Allows creating secrets.
- **update**: Allows modifying existing secrets.
- **delete**: Allows deleting secrets.

---

## Enable KV and Set Secrets

Vault’s **Key-Value (KV) secrets engine** stores secrets as key-value pairs.

### 1. Enable KV Engine

You need to enable the **KV secrets engine** in Vault (if not already done).

#### Enable KV Version 2:

```bash
vault secrets enable -path=secret kv-v2
```

This command enables the **KV version 2** secrets engine at the path `secret/`.

### 2. Put Secrets into Vault

Once KV is enabled, you can store secrets using the `vault kv put` command.

#### Example: Store Secrets for GitLab

```bash
vault kv put secret/gitlab/my-secret username="gitlab_user" password="super_secret_password"
```

This will store the **`username`** and **`password`** for GitLab under the path `secret/gitlab/my-secret`.

---

## Conclusion

1. **AppRole Authentication**: We enabled **AppRole** authentication in Vault and created a **role** called `gitlab-role`.
2. **Policies**: We created a policy `gitlab-secrets-policy` that grants **read** (and possibly **list**) access to Vault secrets under `secret/gitlab/*`.
3. **Role and Secret ID**: We obtained the **Role ID** and **Secret ID** for authenticating with Vault.
4. **Key-Value Access**: We defined access control to secrets stored in Vault using policies for **KV v1** or **KV v2**.

This setup enables secure and fine-grained access control for **GitLab CI/CD** pipelines or any application that needs to authenticate to **Vault** using **AppRole** and retrieve secrets based on policies.

