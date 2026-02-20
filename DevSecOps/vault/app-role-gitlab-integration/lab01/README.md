
# GitLab CI/CD Pipeline for Retrieving Secrets from Vault

This document explains how the provided **GitLab CI/CD pipeline** interacts with **Vault** to retrieve secrets using the **AppRole authentication method**. The pipeline uses Vault to securely retrieve a **secret** (e.g., `DB_PASSWORD`) and uses **environment variables** to authenticate with Vault and retrieve the secrets.

## Table of Contents

1. [Overview](#overview)
2. [Pipeline Steps](#pipeline-steps)
3. [Disadvantages](#disadvantages)

---

## Overview

In this pipeline, we interact with **Vault** using **AppRole authentication** to retrieve secrets such as the `DB_PASSWORD`. The **AppRole** mechanism uses **Role ID** and **Secret ID** for authentication, after which we can obtain the necessary token to access Vault's secrets.

### Key Components:
1. **AppRole Authentication**: The `ROLE_ID` and `SECRET_ID` are used for authentication.
2. **Vault Token**: After authentication, a **Vault token** is generated, which is used for subsequent secret retrieval.
3. **Secret Retrieval**: The secret (`DB_PASSWORD`) is retrieved using `vault kv get`.

---

## Pipeline Steps

Here’s how the pipeline works step by step:

### 1. Define Environment Variables:
- **`ROLE_ID`**: This is the **Role ID** for the `gitlab-role` AppRole.
- **`VAULT_ADDR`**: The address of the Vault server.
- **`SECRET_ID`**: The **Secret ID** for the AppRole, dynamically generated using the Vault CLI.

### 2. Install Required Dependencies:
The pipeline uses **Alpine Linux**, so we install the required dependencies `curl` and `jq` to make API requests and parse JSON responses.

```bash
apk add curl
apk add jq
```

### 3. Generate Secret ID:
We generate the **Secret ID** for the `gitlab-role` using the following command:

```bash
export SECRET_ID=$(vault write -f auth/approle/role/gitlab-role/secret-id -format=json | jq -r '.data.secret_id')
```

This command retrieves a **Secret ID** that will be used for the **AppRole login**.

### 4. Authenticate with Vault using AppRole:
We use **`curl`** to authenticate with Vault by sending the **Role ID** and **Secret ID**:

```bash
curl --request POST --data '{"role_id": "$ROLE_ID", "secret_id": "$SECRET_ID"}' $VAULT_ADDR/v1/auth/approle/login | jq -r '.auth.client_token' > vault_token.txt
```

This command authenticates to Vault and retrieves the **client token** used for further requests. The token is saved in the `vault_token.txt` file.

### 5. Set the Vault Token:
After obtaining the token, we set it as an environment variable for use in subsequent steps:

```bash
export VAULT_TOKEN=$(cat vault_token.txt)
```

### 6. Retrieve Secrets from Vault:
Now that we have the Vault token, we can use it to retrieve the desired secrets. In this case, the secret (`DB_PASSWORD`) is retrieved from the Vault path `secret/gitlab/my-secret`:

```bash
export DB_PASSWORD=$(vault kv get -field=password secret/gitlab/my-secret)
```

The retrieved secret is stored in the `DB_PASSWORD` environment variable.

### 7. Output the Retrieved Secret:
For debugging or verification purposes, we output the secret. **Be cautious with this step in production, as secrets should not be exposed.**

```bash
echo $DB_PASSWORD
```

---

## Disadvantages

While the pipeline works well for retrieving secrets, there are some **disadvantages** to consider, particularly regarding the **rotation of the Secret ID**:

1. **Secret ID Rotation**: The **Secret ID** used for authentication with **AppRole** has a **1-hour expiration** by default. This means that after an hour, the `SECRET_ID` will no longer be valid, and a new **Secret ID** must be generated. In the current pipeline setup, the `SECRET_ID` is generated every time it’s needed, but this can lead to issues if the pipeline takes longer than an hour to run or if the **Secret ID** is not refreshed in time.

2. **Authentication Challenges**: Since the **Secret ID** rotates regularly, the pipeline must be able to dynamically fetch and use the **Secret ID** for every execution. If this is not properly handled, the pipeline might fail due to expired credentials.

3. **Hardcoding Issues**: While not an issue in this specific pipeline, hardcoding sensitive values like `ROLE_ID` and `SECRET_ID` can expose secrets if not properly managed. It's recommended to handle these values securely in environment variables or GitLab CI/CD secret management.

4. **Security Risk with Output**: The pipeline currently outputs the retrieved `DB_PASSWORD` for debugging purposes. **Avoid exposing sensitive data** in logs or outputs, especially in production environments.

---

## Conclusion

This GitLab CI/CD pipeline demonstrates how to securely authenticate with **Vault** using **AppRole**, retrieve secrets, and handle **Secret ID** rotation. However, keep in mind the **disadvantages** related to **Secret ID expiration** and ensure proper handling of sensitive data.
