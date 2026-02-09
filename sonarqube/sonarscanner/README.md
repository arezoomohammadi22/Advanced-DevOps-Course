
# SonarScanner CLI Installation Guide

This README will guide you through the steps to install **SonarScanner CLI** from source, compile it, configure it, and add it to your system's `PATH` so you can use it globally.

---

## Prerequisites

- **Java** and **Maven** installed on your system.
  - To install Java (OpenJDK 11):
    ```bash
    sudo apt install openjdk-11-jdk
    ```

  - To install Maven:
    ```bash
    sudo apt install maven
    ```

---

## Step 1: Download SonarScanner Source Code

1. Download the **SonarScanner CLI** source code from GitHub:
    ```bash
    wget https://github.com/SonarSource/sonar-scanner-cli/archive/refs/tags/8.0.1.6346.tar.gz
    ```

2. Extract the downloaded tarball:
    ```bash
    tar -xvzf sonar-scanner-cli-8.0.1.6346.tar.gz
    ```

3. Navigate to the extracted directory:
    ```bash
    cd sonar-scanner-cli-8.0.1.6346
    ```

---

## Step 2: Compile SonarScanner CLI

1. Ensure **Java** and **Maven** are installed (as mentioned in prerequisites).

2. Compile **SonarScanner CLI** by running Maven:
    ```bash
    mvn clean install
    ```

3. This will create the **SonarScanner CLI executable** inside the `target/` directory.

---

## Step 3: Check the Correct Directory for the Executable

1. After compiling, check the `bin/` directory for the `sonar-scanner` executable:
    ```bash
    cd /path/to/sonar-scanner-cli-8.0.1-SNAPSHOT/
    ls bin/
    ```

2. You should see the **`sonar-scanner`** executable inside the `bin/` folder. If it’s missing, try downloading a precompiled binary instead.

---

## Step 4: Make the Executable Work

1. If you found the `sonar-scanner` binary, ensure it’s **executable**:
    ```bash
    chmod +x sonar-scanner
    ```

2. Verify by running:
    ```bash
    ./sonar-scanner --version
    ```

---

## Step 5: Add SonarScanner to the PATH

1. Edit your `~/.bashrc` (or `~/.zshrc` if using Zsh) file:
    ```bash
    nano ~/.bashrc  # Or ~/.zshrc if using Zsh
    ```

2. Add the following lines to the end of the file:
    ```bash
    export SONAR_SCANNER_HOME=/root/sonar-scanner-cli-8.0.1.6346/target/sonar-scanner-8.0.1-SNAPSHOT
    export PATH=$PATH:$SONAR_SCANNER_HOME/bin
    ```

3. Apply the changes:
    ```bash
    source ~/.bashrc  # Or source ~/.zshrc if using Zsh
    ```

---

## Step 6: Verify Installation

1. After adding it to your `PATH`, verify the installation:
    ```bash
    sonar-scanner --version
    ```

---

## Step 7: Using SonarScanner

1. Once SonarScanner is installed and available in your `PATH`, you can use it to analyze your project.

2. Navigate to the directory containing your project and run the following command:
    ```bash
    sonar-scanner -Dsonar.projectKey=your_project_key -Dsonar.host.url=http://localhost:9000 -Dsonar.login=your_sonar_token
    ```

3. This will send the analysis results to your **SonarQube server**.

---

## Conclusion

You have successfully compiled and installed **SonarScanner CLI** from source and added it to your system’s `PATH`. You can now use it to perform code quality analysis and integrate it into your CI/CD pipeline.
