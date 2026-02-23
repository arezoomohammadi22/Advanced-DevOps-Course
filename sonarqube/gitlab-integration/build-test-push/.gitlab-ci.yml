stages:
  - build
  - test
  - sonar_analysis
  - trivy_scan  # New stage for Trivy security scan
  - deploy  # Optional, if you're deploying after passing tests

variables:
  SONAR_TOKEN: ""
  SONAR_HOST_URL: http://10.211.55.68:9000
  TRIVY_VERSION: "0.69.1"  # Specify the version of Trivy to use


# Define cache for Python dependencies to speed up the pipeline
cache:
  paths:
    - .venv/
    - venv/
    - pip-cache/

# SonarQube Analysis Stage
sonar_analysis:
  stage: sonar_analysis
  tags:
    - shell
  script:
    - echo "Starting SonarQube analysis..."
    - sonar-scanner -Dsonar.projectKey=$CI_PROJECT_NAME -Dsonar.sources=. -Dsonar.qualitygate.wait=true 
  only:
    - main
  allow_failure: false

# Build and Push Docker Image Stage
build-and-push:
  stage: build
  tags:
    - k8s
  image: docker:27
  services:
    - name: docker:27-dind
      command: ["--tls=false"]
  variables:
    DOCKER_HOST: tcp://docker:2375
    DOCKER_TLS_CERTDIR: ""
    IMAGE_TAG: "$CI_COMMIT_SHORT_SHA"
  script:
    - docker info
    - cat /etc/hosts
    - echo "$CI_REGISTRY_PASSWORD" | docker login "$CI_REGISTRY" -u "$CI_REGISTRY_USER" --password-stdin
    - docker build -t "$CI_REGISTRY_IMAGE:$IMAGE_TAG" -t "$CI_REGISTRY_IMAGE:latest" .
    - docker push "$CI_REGISTRY_IMAGE:$IMAGE_TAG"
    - docker push "$CI_REGISTRY_IMAGE:latest"

# Trivy Scan Stage
trivy_scan:
  stage: trivy_scan
  image: aquasec/trivy:$TRIVY_VERSION  # Use the official Trivy Docker image
  tags:
    - shell
  script:
    - echo "Running Trivy container scan..."
    # Login to GitLab Registry before pulling the image for scanning
    - echo "$CI_REGISTRY_PASSWORD" | docker login "$CI_REGISTRY" -u "$CI_REGISTRY_USER" --password-stdin
    - trivy image --exit-code 1 --no-progress "$CI_REGISTRY_IMAGE:$IMAGE_TAG"  # Scan the image
  only:
    - main  # Run Trivy scan only on the main branch
  allow_failure: false  # Fail the pipeline if vulnerabilities are found

# Optional Deploy Stage
deploy:
  stage: deploy
  script:
    - echo "Deploying the project..."
  tags:
    - shell
