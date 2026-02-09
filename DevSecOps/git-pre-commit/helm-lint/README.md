# Pre-commit Configuration and Helm Linting with GitLab CI/CD

This **README** provides an overview of how to configure **Pre-commit hooks** and **Helm linting** in a **GitLab CI/CD pipeline**.

## Pre-commit Hooks Configuration

### Repositories and Hooks

The following **Pre-commit hooks** are used in the configuration:

1. **YAML Syntax Check (`check-yaml`)**
    - Validates YAML syntax in files.
    - **Auto-fix**: No.
2. **End-of-file Fixer (`end-of-file-fixer`)**
    - Adds missing newlines at the end of files.
    - **Auto-fix**: Yes.
3. **Trailing Whitespace Remover (`trailing-whitespace`)**
    - Removes trailing whitespace from lines in files.
    - **Auto-fix**: Yes.
4. **Python Code Formatter (`black`)**
    - Formats Python code following **PEP-8** guidelines.
    - **Auto-fix**: Yes.
5. **Secret Detection (`detect-secrets`)**
    - Detects hardcoded secrets (API keys, passwords, etc.) in files.
    - **Auto-fix**: No.
6. **Dockerfile Linter (`hadolint`)**
    - Lints Dockerfiles for security issues and best practices.
    - **Auto-fix**: No.

### Example of `.pre-commit-config.yaml`
```yaml
repos:
  # Syntax and code quality checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v2.3.0
    hooks:
      - id: check-yaml   # YAML syntax check
      - id: end-of-file-fixer  # Fixes missing newline at the end of files
      - id: trailing-whitespace  # Removes trailing whitespace

  # Python code formatting with Black
  - repo: https://github.com/psf/black
    rev: 22.10.0
    hooks:
      - id: black   # Formats Python code

  # Secret scanning to detect hardcoded secrets
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.0.3
    hooks:
      - id: detect-secrets
        name: Detect Secrets
        files: \.(py|yaml|json|env)$

  # Dockerfile security checks with Hadolint
  - repo: https://github.com/hadolint/hadolint
    rev: v2.10.0
    hooks:
      - id: hadolint   # Lints Dockerfiles for security issues
        name: Dockerfile Linter
        files: Dockerfile

