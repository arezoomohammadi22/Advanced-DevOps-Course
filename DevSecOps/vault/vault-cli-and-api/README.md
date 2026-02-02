
# Vault CLI Commands, REST API Guide, and Available Endpoints

## Table of Contents

1. [Unseal Vault](#unseal-vault)
2. [Port Forwarding and Access Vault](#port-forwarding-and-access-vault)
3. [Login Using Token](#login-using-token)
4. [Working with Vault CLI](#working-with-vault-cli)
5. [Working with Vault REST API](#working-with-vault-rest-api)
6. [Available CLI Commands and API Endpoints](#available-cli-commands-and-api-endpoints)

---

## 1. Unseal Vault

Vault is **sealed** by default for security. To unseal it, follow these steps:

### Step 1: Initialize Vault

When Vault is first deployed, it must be initialized. You can initialize it by running:

```bash
kubectl exec -it vault-0 -- vault operator init
```

This command will return 5 unseal keys and the **root token**. Keep these keys secure.

### Step 2: Unseal Vault

Vault requires **3 out of 5 unseal keys** to unseal it. You can unseal Vault by providing the unseal keys one by one. Run the following command to unseal Vault for the first key:

```bash
kubectl exec -it vault-0 -- vault operator unseal <unseal_key_1>
```

Repeat this command for the other unseal keys:

```bash
kubectl exec -it vault-0 -- vault operator unseal <unseal_key_2>
kubectl exec -it vault-0 -- vault operator unseal <unseal_key_3>
```

Once 3 keys are provided, Vault will be unsealed and operational.

**Note**: You only need to unseal Vault once unless Vault is restarted or its state is reset.

---

## 2. Port Forwarding and Access Vault

To access Vault from your local machine, you need to **port forward** the Vault service to make it accessible on your local machine.

### Step 1: Port Forward Vault Service

Run the following command to forward Vault’s service to your local machine:

```bash
kubectl port-forward svc/vault 8200:8200
```

This will make Vault accessible at `http://localhost:8200` in your web browser.

---

## 3. Login Using Token

Once Vault is running and unsealed, you can **log in** using the **root token** or a **newly generated token**.

### Step 1: Log in to Vault (Web UI)

- Open your browser and navigate to `http://localhost:8200`.
- On the login screen, select **Token** as the authentication method.
- Enter the **root token** (or a valid token you generated) that was printed during the initialization process.
  
  **Example**:  
  ```bash
  vault login <root_token>
  ```

  Once logged in, you’ll have full access to Vault.

### Step 2: Generate a New Token

If you want to create a new token for logging in (instead of using the root token), follow these steps:

1. **Log in** with the root token or an existing token.
   
   ```bash
   vault login <root_token>
   ```

2. **Create a new token** using the following command:

   ```bash
   vault token create -policy=default
   ```

   This will generate a new token with the `default` policy.

3. **Log in with the new token**:

   - Go to the Vault Web UI at `http://localhost:8200`.
   - Choose **Token** authentication and enter the new token generated in the previous step.

---

## 4. Working with Vault CLI

The **Vault CLI** allows you to interact with Vault via command line. Here are some common CLI commands:

- **Login**: Log into Vault using a token.
  ```bash
  vault login <root_token>
  ```

- **Write Secret**: Write secrets to a specific path.
  ```bash
  vault kv put secret/mysecret key=value
  ```

- **Read Secret**: Read a secret from a specific path.
  ```bash
  vault kv get secret/mysecret
  ```

- **Create a Token**: Create a new token.
  ```bash
  vault token create -policy=default
  ```

- **Revoke Token**: Revoke a token.
  ```bash
  vault token revoke <token_to_revoke>
  ```

- **List Tokens**: List active tokens.
  ```bash
  vault token list
  ```

- **Unseal Vault**: Unseal Vault by providing unseal keys.
  ```bash
  vault operator unseal <unseal_key>
  ```

- **Create/Manage Policies**: Write and manage policies.
  ```bash
  vault policy write <policy_name> <policy_file>
  ```

---

## 5. Working with Vault REST API

Vault exposes a **REST API** that you can use to perform actions programmatically. Some common API operations include:

- **Read a Secret** (from the Key-Value store):
  ```bash
  curl --header "X-Vault-Token: <your_token>" http://localhost:8200/v1/secret/data/mysecret
  ```

- **Create a New User (Userpass)**:
  ```bash
  curl --header "X-Vault-Token: <your_token>" --request POST --data '{"password": "my-password", "policies": ["default"]}' http://localhost:8200/v1/auth/userpass/users/john
  ```

- **Login with Userpass**:
  ```bash
  curl --request POST --data '{"password": "my-password"}' http://localhost:8200/v1/auth/userpass/login/john
  ```

- **Create a New Token**:
  ```bash
  curl --header "X-Vault-Token: <your_token>" --request POST --data '{"policies": ["default"]}' http://localhost:8200/v1/auth/token/create
  ```

- **Lookup Token**:
  ```bash
  curl --header "X-Vault-Token: <your_token>" http://localhost:8200/v1/auth/token/lookup-self
  ```

- **Revoke Token**:
  ```bash
  curl --header "X-Vault-Token: <your_token>" --request POST --data '{"token": "<token_to_revoke>"}' http://localhost:8200/v1/auth/token/revoke
  ```

- **List Tokens**:
  ```bash
  curl --header "X-Vault-Token: <your_token>" http://localhost:8200/v1/auth/token/lookup
  ```

---

## 6. Available CLI Commands and API Endpoints

| Operation         | Vault CLI Command                                     | REST API Request                                                                 |
|-------------------|-------------------------------------------------------|----------------------------------------------------------------------------------|
| **Get Secret**     | `vault kv get secret/mysecret`                        | `curl --header "X-Vault-Token: <your_token>" http://localhost:8200/v1/secret/data/mysecret` |
| **Get User List**  | `vault list auth/userpass/users`                      | `curl --header "X-Vault-Token: <your_token>" http://localhost:8200/v1/auth/userpass/users` |
| **Create Token**   | `vault token create -policy=default`                  | `curl --header "X-Vault-Token: <your_token>" --request POST --data '{"policies": ["default"]}' http://localhost:8200/v1/auth/token/create` |
| **Login (Userpass)**| `vault login <root_token>`                           | `curl --request POST --data '{"password": "my-password"}' http://localhost:8200/v1/auth/userpass/login/john` |
| **Revoke Token**   | `vault token revoke <token_to_revoke>`                | `curl --header "X-Vault-Token: <your_token>" --request POST --data '{"token": "<token_to_revoke>"}' http://localhost:8200/v1/auth/token/revoke` |
| **List Tokens**    | `vault token list`                                    | `curl --header "X-Vault-Token: <your_token>" http://localhost:8200/v1/auth/token/lookup` |

---

### Conclusion

This guide provided instructions for unsealing Vault, logging in using tokens, and working with Vault via both the **CLI** and **REST API**. You now have expanded examples of CLI commands and API requests for managing secrets, users, tokens, and more.


