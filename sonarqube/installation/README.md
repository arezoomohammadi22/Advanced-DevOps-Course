
# SonarQube with Docker and PostgreSQL Setup

This is a simple setup to run SonarQube with PostgreSQL using Docker Compose.

## Prerequisites

- Docker
- Docker Compose

## Setup

2. Create a `docker-compose.yml` file with the following content:

    ```yaml
    version: '3'
    services:
      sonarqube:
        image: sonarqube:latest
        container_name: sonarqube
        ports:
          - "9000:9000"
        environment:
          - SONARQUBE_JDBC_URL=jdbc:postgresql://db:5432/sonar
        networks:
          - sonarnet
      db:
        image: postgres:latest
        container_name: sonarqube_db
        environment:
          - POSTGRES_USER=sonar
          - POSTGRES_PASSWORD=sonar
          - POSTGRES_DB=sonar
        networks:
          - sonarnet
    networks:
      sonarnet:
        driver: bridge
    ```

3. Start the services:

    ```bash
    docker-compose up -d
    ```

    This will start the SonarQube and PostgreSQL containers in detached mode.

## Access the SonarQube UI

Once the containers are up and running, you can access the SonarQube UI by navigating to the following URL in your browser:

- `http://localhost:9000`

## Default Login Credentials

The default login credentials for SonarQube are:

- **Username**: `admin`
- **Password**: `admin`

It is recommended to change the default password after your first login.

## Stopping the Services

To stop the SonarQube and PostgreSQL containers, you can run:

```bash
docker-compose down
```

This will stop and remove the containers. Your data will be preserved in the PostgreSQL container unless you explicitly remove the volume.
