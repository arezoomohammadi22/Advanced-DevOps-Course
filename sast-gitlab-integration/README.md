
# GitLab CI/CD for SAST and Security Scans

This repository is configured with a GitLab CI/CD pipeline to run both test and security scans using Semgrep. The pipeline is divided into two stages: **test** and **security**. In the **security** stage, the **Semgrep** tool is used to scan for vulnerabilities in the code, such as hardcoded secrets.

## Stages in `.gitlab-ci.yml`

### 1. Test Stage
The **test** stage is designed to run basic tests for the application.
```yaml
  test:
    script:
      - echo "This is the testing stage"
    stage: test
    tags:
      - docker-dedicated
```

### 2. Security Stage
The **security** stage runs a security scan using **Semgrep**, focusing on detecting security issues in the code, including hardcoded secrets like API keys and AWS access keys.
```yaml
  security_scan:
    script:
      - echo "Running security scan with Semgrep"
      - semgrep --config https://semgrep.dev/p/secrets-python  # Use the Semgrep ruleset for secrets detection
    stage: security  # Ensure this is the security stage
    tags:
      - docker-dedicated
```

### Docker-Dedicated Executor Runner
To run the pipeline properly, the GitLab Runner needs to be configured with the **docker-dedicated executor**. This ensures that the necessary containers for running security scans are available and isolated from the host machine.

## Example Vulnerable Code
The following Python code is an example of a security vulnerability (unsafe use of `eval()`):
```python
  def unsafe_eval(user_input):
      result = eval(user_input)  # Using eval() unsafely
      return result

  user_input = input("Enter an expression to evaluate: ")
  print(unsafe_eval(user_input))
```

In this case, Semgrep will detect the unsafe use of `eval()` and flag it as a potential security risk.

## Files in this Repository
- **.gitlab-ci.yml**: GitLab CI/CD configuration file that defines the pipeline stages and jobs.
- **README.md**: Documentation file for the repository setup and usage instructions.
- **App Code**: The application code that will be scanned by the CI pipeline.

## Requirements
To use this configuration in your GitLab project, you need to have a GitLab Runner configured with the **docker-dedicated executor** to ensure proper execution of the Semgrep scans in isolated environments.
