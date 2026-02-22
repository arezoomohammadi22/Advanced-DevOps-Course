
# KubiScan Installation and Usage Guide

**CyberArk KubiScan** is a tool to scan Kubernetes clusters for risky roles, role bindings, subjects, pods, and containers.

## Step 1: Clone the KubiScan Repository

Start by cloning the KubiScan repository from GitHub:

```bash
git clone https://github.com/cyberark/KubiScan.git
```

After cloning, navigate to the KubiScan directory:

```bash
cd KubiScan
```

## Step 2: Install Dependencies

### 2.1 Install Python Dependencies

KubiScan requires Python 3 and several dependencies to run. You can install the required dependencies by running:

```bash
pip install -r requirements.txt
```

Alternatively, if you haven't installed the **Kubernetes** Python client yet, install it manually:

```bash
pip install kubernetes
```

### 2.2 Install PrettyTable

Another required package is **PrettyTable**:

```bash
pip install PTable
```

## Step 3: Running KubiScan

### 3.1 General Usage

Once dependencies are installed, you can run **KubiScan** directly using the following command:

```bash
python3 KubiScan.py
```

### 3.2 Common Commands

Here are some of the most commonly used commands with **KubiScan**:

#### Scan Risky Roles

- Get all risky Roles:
  ```bash
  python3 KubiScan.py -rr
  ```
- Get all risky ClusterRoles:
  ```bash
  python3 KubiScan.py -rcr
  ```
- Get both risky Roles and ClusterRoles:
  ```bash
  python3 KubiScan.py -rar
  ```

#### Scan Risky RoleBindings

- Get all risky RoleBindings:
  ```bash
  python3 KubiScan.py -rb
  ```
- Get all risky ClusterRoleBindings:
  ```bash
  python3 KubiScan.py -rcb
  ```
- Get both risky RoleBindings and ClusterRoleBindings:
  ```bash
  python3 KubiScan.py -rab
  ```

#### Scan Risky Subjects (Users, Groups, Service Accounts)

- Get all risky Subjects:
  ```bash
  python3 KubiScan.py -rs
  ```

#### Scan Risky Pods

- Get all risky Pods/Containers:
  ```bash
  python3 KubiScan.py -rp
  ```
- Add the `-d` flag to scan deeper into running pods:
  ```bash
  python3 KubiScan.py -rp -d
  ```

#### Scan Privileged Pods

- Get all privileged Pods/Containers:
  ```bash
  python3 KubiScan.py -pp
  ```

#### Scan All Resources

- Get all risky Roles, RoleBindings, Subjects, and Pods:
  ```bash
  python3 KubiScan.py -a
  ```

#### Scan for CVEs (Common Vulnerabilities and Exposures)

- Scan for CVEs in your cluster:
  ```bash
  python3 KubiScan.py -cve
  ```

### 3.3 Using Additional Flags

- **Scan by Context**:
  If you want to scan a specific Kubernetes context:
  ```bash
  python3 KubiScan.py -ctx <context_name>
  ```

- **Filter by Priority**:
  Filter results by priority (e.g., CRITICAL, HIGH, LOW):
  ```bash
  python3 KubiScan.py -p CRITICAL
  ```

- **Export Results to JSON**:
  Export the scan results in JSON format:
  ```bash
  python3 KubiScan.py -j output.json
  ```

### 3.4 Example Command

To get all risky Roles, RoleBindings, Pods, and Subjects and export the results to a JSON file, use:

```bash
python3 KubiScan.py -a -j risky_scan_output.json
```

## Step 4: Scan for Associated RoleBindings/ClusterRoleBindings

If you need to list associated RoleBindings/ClusterRoleBindings for a specific Role or ClusterRole:

- **Associated RoleBindings for Role**:
  ```bash
  python3 KubiScan.py -aarbr "read-secrets-role" -ns "default"
  ```

- **Associated RoleBindings for ClusterRole**:
  ```bash
  python3 KubiScan.py -aarbcr "read-secrets-clusterrole"
  ```

- **Associated RoleBindings for Subject (User, Group, Service Account)**:
  ```bash
  python3 KubiScan.py -aarbs "system:masters" -k "Group"
  ```

- **Associated Roles/ClusterRoles for Subject**:
  ```bash
  python3 KubiScan.py -aars "generic-garbage-collector" -k "ServiceAccount" -ns "kube-system"
  ```

## Step 5: Dump Tokens from Pods

You can dump tokens from pods using the `-dt` flag. Here are a few examples:

- Dump tokens from all pods:
  ```bash
  python3 KubiScan.py -dt
  ```

- Dump tokens from a specific namespace or pod:
  ```bash
  python3 KubiScan.py -dt -ns "kube-system" -n "nginx1"
  ```

## Step 6: Remote Access (Optional)

If you need to scan using a remote Kubernetes cluster, you can specify the master IP and port, as well as certificates and tokens:

- **Remote Master Host**:
  ```bash
  python3 KubiScan.py -ho <MASTER_IP>:<PORT>
  ```

- **Remote Certificates and Tokens**:
  ```bash
  python3 KubiScan.py -cc /path/to/client-certificate -ck /path/to/client-key -co /path/to/kubeconfig -t /path/to/token
  ```

### 3.7 Additional Options:

- **Quiet Mode**: Suppress the banner output:
  ```bash
  python3 KubiScan.py -q
  ```

- **Output to File**: Save the results to a file:
  ```bash
  python3 KubiScan.py -o output.txt
  ```

