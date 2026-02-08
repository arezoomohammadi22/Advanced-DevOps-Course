
# Hadolint Dockerfile Linter Setup with Pre-commit

This guide demonstrates how to set up **Hadolint** (Dockerfile Linter) and integrate it with **Pre-commit hooks** to automatically lint Dockerfiles, check YAML files, format Python code, and detect secrets before committing to your Git repository.

## Prerequisites

- **Python**: Make sure Python is installed on your system.
- **Git**: Ensure Git is installed for version control.
- **Pre-commit**: You will need to install the `pre-commit` tool to run the hooks.

## Step 1: Install Hadolint on Ubuntu (ARM-Based Systems)

1. Download the Hadolint binary for ARM architecture:
   ```bash
   wget https://github.com/hadolint/hadolint/releases/download/v2.14.0/hadolint-linux-arm64
   ```

2. Make the binary executable:
   ```bash
   chmod +x hadolint-linux-arm64
   ```

3. Move the binary to a directory in your system's `PATH`:
   ```bash
   sudo mv hadolint-linux-arm64 /usr/local/bin/hadolint
   ```

4. Verify the installation by checking the version:
   ```bash
   hadolint --version
   ```

## Step 2: Install Pre-commit and Set Up Hooks

1. Install `pre-commit` using pip:
   ```bash
   pip install pre-commit
   ```

2. Create a `.pre-commit-config.yaml` file in the root of your repository with the following content:

```yaml
repos:
  # Syntax and code quality checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v2.3.0
    hooks:
      - id: check-yaml
      - id: end-of-file-fixer
      - id: trailing-whitespace

  - repo: https://github.com/psf/black
    rev: 22.10.0
    hooks:
      - id: black

  # Secret scanning
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.0.3
    hooks:
      - id: detect-secrets
        name: Detect Secrets
        files: \.(py|yaml|json|env)$

  # Dockerfile security checks
  - repo: https://github.com/hadolint/hadolint
    rev: v2.10.0
    hooks:
      - id: hadolint
        name: Dockerfile Linter
        files: Dockerfile
```

3. Install the pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Step 3: Dockerfile Example

Here’s a sample Dockerfile with security and best practice issues:

```Dockerfile
# Sample Dockerfile with security issues
FROM ubuntu:20.04

# Update and install packages (bad practice)
RUN apt-get update && apt-get install -y curl

# Exposing ports (bad practice to expose unnecessary ports)
EXPOSE 80

# Running a command without setting a user (security issue)
RUN curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh

# Adding a secret in plain text (security issue)
RUN echo "MY_SECRET_API_KEY=12345" > /my_secrets.txt

# Create a directory but no specific user to run the application
WORKDIR /app
```

**Hadolint** will flag the following issues:
- **Running commands as root**.
- **Exposing unnecessary ports**.
- **Hardcoding secrets in Dockerfile**.

## Step 4: Test Pre-commit Hooks

1. **Create or modify your Dockerfile** (as shown above with issues).
2. **Add the file** to the staging area:
   ```bash
   git add Dockerfile
   ```

3. **Commit the changes**:
   ```bash
   git commit -m "Test Dockerfile linting"
   ```

4. **Pre-commit will automatically run Hadolint**, and it will check the Dockerfile for issues. If there are issues (e.g., exposed ports or hardcoded secrets), the commit will be blocked, and you'll see feedback like:

```bash
hadolint....................................................Failed
- hook id: hadolint
- exit code: 1
- files were modified by this hook

Warning: Avoid using 'EXPOSE' without reason.
```

## Step 5: Using Hadolint for Other Files

You can also use Pre-commit hooks to check YAML files, Python code formatting, and detect secrets in your code.

1. **Test YAML Linting**:
   Create an invalid YAML file and run the commit:

   ```yaml
   key1: value1
   key2: value2
     key3: value3   # Incorrect indentation here
   ```

   Pre-commit will block the commit with the error:

   ```bash
   check-yaml....................................................................Failed
   - hook id: check-yaml
   - exit code: 1
   test.yaml: line 4: could not find expected ':'
   ```

2. **Test Python Code Formatting (with Black)**:
   Create a Python file with incorrect formatting:

   ```python
   def example_function():
     print("Hello, world!")
   ```

   Pre-commit will auto-format the code using **Black**.

---

## Conclusion

By integrating **Hadolint** with **Pre-commit**:
- You can automatically lint your Dockerfiles, ensure security best practices, and catch errors before committing.
- **Pre-commit hooks** help maintain code quality by checking YAML syntax, Python code formatting, and detecting hardcoded secrets in your files.


