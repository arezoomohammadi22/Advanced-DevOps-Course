
# Project CI/CD Setup with GitLab and SonarQube

This project is configured to use **SonarQube** for static code analysis as part of the CI/CD pipeline on **GitLab**. Below is a step-by-step guide to setting up the environment and configuring GitLab CI/CD with SonarQube integration.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Setting up SonarQube](#setting-up-sonarqube)
- [GitLab CI/CD Configuration](#gitlab-cicd-configuration)
- [Setting Up Environment Variables](#setting-up-environment-variables)
- [Quality Gate in SonarQube](#quality-gate-in-sonarqube)

## Prerequisites

Ensure the following tools and services are set up:

- **SonarQube** instance (Community Edition or any version that supports analysis)
- **GitLab CI/CD** setup for your project
- **Docker** (if using Docker runners in GitLab)
- **Python 3** and `pip` for the environment setup

## Setting up SonarQube

1. **Install SonarQube**:
   - You can install SonarQube locally or use a hosted instance.
   - Follow the [SonarQube installation documentation](https://docs.sonarqube.org/latest/setup/install-server/) to install SonarQube if not already set up.

2. **Create a SonarQube Project**:
   - In your SonarQube instance, create a new project for your repository.
   - You will need to retrieve your **SonarQube project key** and **authentication token** from the project page to use in the pipeline configuration.

## GitLab CI/CD Configuration

### .gitlab-ci.yml

Here is the configuration for `.gitlab-ci.yml` that sets up the pipeline for SonarQube analysis:

```yaml
stages:
  - build
  - sonar_analysis
  - deploy  # Optional, if you're deploying after passing tests

# Cache Python dependencies
cache:
  paths:
    - .venv/
    - venv/
    - pip-cache/

# Install dependencies and prepare the environment
before_script:
  - python3 --version
  - pip install --upgrade pip
  - pip install -r requirements.txt  # Install Python dependencies
  - pip install pytest-cov  # Ensure pytest-cov is installed for coverage

# Build Stage
build:
  stage: build
  tags:
    - shell
  script:
    - echo "Building the Python Flask project..."
    - python3 -m compileall .  # Compile all the Python files (optional)

# SonarQube Analysis Stage
sonar_analysis:
  stage: sonar_analysis
  tags:
    - shell
  script:
    - echo "Starting SonarQube analysis..."
    - sonar-scanner         -Dsonar.projectKey="$CI_PROJECT_PATH_SLUG"         -Dsonar.sources=.         -Dsonar.tests=tests         -Dsonar.python.coverage.reportPaths=coverage.xml         -Dsonar.host.url=$SONAR_HOST_URL         -Dsonar.login=$SONARQUBE_TOKEN         -Dsonar.qualitygate.wait=true  # Wait for the quality gate status
  only:
    - main  # Run SonarQube only on the main branch

# Deploy Stage (optional)
deploy:
  stage: deploy
  script:
    - echo "Deploying the project..."
    - ./deploy.sh  # Replace with your deployment script
```

### Explanation:
- **Build Stage**: Compiles the Python Flask project (optional).
- **SonarQube Analysis**: Runs the `sonar-scanner` and sends the results to your SonarQube instance. The `sonar.qualitygate.wait=true` ensures the pipeline waits for SonarQube quality gate status before continuing.
- **Deploy Stage**: Deploys the application if all stages pass (optional).

## Setting Up Environment Variables

1. **SonarQube Token**:
   - You need to set up the **SonarQube token** in GitLab as an environment variable for secure access during the SonarQube scan.
   - Navigate to **GitLab Project Settings > CI/CD > Variables** and add a variable named:
     - **SONARQUBE_TOKEN**: The token you generated in SonarQube.
   - This will be used in the `sonar.login=$SONARQUBE_TOKEN` part of the configuration.

2. **SonarQube Host URL**:
   - Set up the **SonarQube host URL** as an environment variable:
     - **SONAR_HOST_URL**: The URL of your SonarQube server (e.g., `http://localhost:9000` for a local instance).
   - Add this variable in **GitLab Project Settings > CI/CD > Variables**.

## Quality Gate in SonarQube

A **Quality Gate** ensures that your project meets a set of defined quality standards before proceeding with deployment or other stages. For SonarQube:

1. **Create or Modify a Quality Gate**:
   - Navigate to **Quality Gates** in your SonarQube instance.
   - Create a new quality gate or modify an existing one.
   - Add conditions to fail the gate based on rules like:
     - **No new security vulnerabilities**.
     - **Coverage on new code >= 80%**.
     - **No new bugs**.

2. **Configure the Quality Gate**:
   - After defining your quality gate, make sure to apply it to your project.

3. **Wait for Quality Gate in CI/CD**:
   - In the `.gitlab-ci.yml`, we use the `-Dsonar.qualitygate.wait=true` to make the pipeline wait for the quality gate status. If the quality gate fails, the pipeline will fail as well.

## Conclusion

This setup integrates **SonarQube** into your **GitLab CI/CD pipeline**, ensuring that your **new code** meets quality standards and that any vulnerabilities or bugs are detected early. By using **SonarQube tokens** and environment variables, you maintain secure and efficient scanning of your codebase.

Make sure to configure your **Quality Gate** in SonarQube and adjust your pipeline configuration accordingly. This will help maintain high standards of code quality and security across your project.

