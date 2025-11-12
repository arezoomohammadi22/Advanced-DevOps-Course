# Filebeat + Docker Logs over HTTPS (Internal CA)
This README gives you two production‑ready ways to ship **Docker container logs** with Filebeat to **Elasticsearch over HTTPS** using your **internal CA**.

- **Option A (Simple & Solid):** `filestream` + `container` parser — reads all container JSON logs under `/var/lib/docker/containers/*/*.log`.
- **Option B (Dynamic):** Docker **autodiscover** with **hints** — only collects logs for containers you label.

> Assumptions (Debian/Ubuntu package install):
> - Config: `/etc/filebeat/filebeat.yml`
> - Service: `systemctl` managed
> - Elasticsearch is on HTTPS and you have the **root CA** (or chain) that signed its cert.

---

## 0) Put your internal CA on the Filebeat host
```bash
sudo mkdir -p /etc/filebeat/certs
sudo cp ~/cacert.pem /etc/filebeat/certs/ca.crt
sudo chown root:root /etc/filebeat/certs/ca.crt
sudo chmod 0644 /etc/filebeat/certs/ca.crt
```

---

## 1) Verify TLS to Elasticsearch with curl
Adjust as needed:
```bash
ES_HOST="10.211.55.63"
ES_PORT="9200"
ES_USER="sananet"
ES_PASS="123456"
CA_FILE="/etc/filebeat/certs/ca.crt"

curl -s --cacert "$CA_FILE" -u "$ES_USER:$ES_PASS" "https://$ES_HOST:$ES_PORT"
```
- A JSON response == TLS/Auth OK.
- If you hit a **hostname mismatch** (cert issued for a hostname but you connect via IP), either use the proper hostname (recommended) or temporarily relax hostname verification in Filebeat (see below).

---

## 2) Option A — filestream + container parser (recommended to start)
Collects all container logs and enriches with Docker metadata.

```yaml
# /etc/filebeat/filebeat.yml
filebeat.inputs:
  - type: filestream
    id: docker-logs
    enabled: true
    paths:
      - /var/lib/docker/containers/*/*.log

    # Parse Docker JSON log lines reliably
    parsers:
      - container:
          stream: all

    # Optional: better discoverability in Kibana (Data Streams)
    data_stream.dataset: "docker"
    data_stream.namespace: "prod"

    # Optional: allow ingesting very small log files (<1KB default fingerprint)
    # prospector.scanner.fingerprint.length: 256
    # prospector.scanner.fingerprint.offset: 0

filebeat.modules: []

processors:
  - add_docker_metadata: ~

output.elasticsearch:
  hosts: ["https://10.211.55.63:9200"]
  username: "sananet"
  password: "123456"
  ssl:
    certificate_authorities: ["/etc/filebeat/certs/ca.crt"]
    # If connecting via IP while the cert is for a hostname, you can temporarily use:
    # verification_mode: certificate
```
**Notes**
- Filebeat (Debian pkg) runs as root by default → can read `/var/lib/docker/containers`.
- Data goes to **Data Streams**: look for `logs-docker-prod` in Kibana’s **Stack Management → Data Streams**.

---

## 3) Option B — Autodiscover with hints
Collect logs only from containers you label (or based on conditions).

```yaml
# /etc/filebeat/filebeat.yml
filebeat.autodiscover:
  providers:
    - type: docker
      hints.enabled: true
      templates:
        - condition:
            contains:
              docker.container.labels.co.elastic.logs/enabled: "true"
          config:
            - type: filestream
              paths:
                - /var/lib/docker/containers/${data.docker.container.id}/*.log
              parsers:
                - container:
                    stream: all
              data_stream.dataset: "docker"
              data_stream.namespace: "prod"

processors:
  - add_docker_metadata: ~

output.elasticsearch:
  hosts: ["https://10.211.55.63:9200"]
  username: "sananet"
  password: "123456"
  ssl:
    certificate_authorities: ["/etc/filebeat/certs/ca.crt"]
    # verification_mode: certificate
```
Label the containers you want to collect:
```bash
docker run -d \
  --label co.elastic.logs/enabled=true \
  --name myapp \
  myimage:latest
```
**Docker Compose example:**
```yaml
services:
  myapp:
    image: myimage:latest
    labels:
      co.elastic.logs/enabled: "true"
```

---

## 4) Test Filebeat configuration & connection
```bash
sudo filebeat test config -e
sudo filebeat test output -e
```
- `Config OK` + `talk to Elasticsearch ... succeed` = ready to go.

---

## 5) (Optional) Generate a test container & logs
Start a noisy container to produce logs:
```bash
docker run --rm -d --name loggen --label co.elastic.logs/enabled=true busybox \
  sh -c 'i=0; while true; do i=$((i+1)); echo "$(date -Is) hello from container $i"; sleep 1; done'
```
Stop it later:
```bash
docker stop loggen
```

---

## 6) Restart Filebeat & tail logs
```bash
sudo systemctl restart filebeat
sudo journalctl -u filebeat -n 200 --no-pager
```
Look for:
- `Harvester started for file: /var/lib/docker/containers/.../*.log`
- `Connected to Elasticsearch`

---

## 7) Confirm ingestion (Data Streams)
```bash
curl -s --cacert "$CA_FILE" -u "$ES_USER:$ES_PASS" "https://$ES_HOST:$ES_PORT/_data_stream?pretty"
```
You should see `logs-docker-prod`. In Kibana → **Stack Management → Data Streams**, open it and use **Discover**.

---

## 8) Optional: Trim noisy fields
Keep enrichment but drop heavy/unused fields:
```yaml
processors:
  - add_docker_metadata: ~
  - drop_fields:
      ignore_missing: true
      fields:
        - cloud
        - orchestrator
        - kubernetes
        - log.offset
        - log.file.device_id
        - log.file.inode
```
For ultra‑minimal payloads, you *can* use `include_fields`, but dashboard compat may suffer.

---

## 9) Security best practices
- Prefer **API Keys** over basic auth:
  ```bash
  sudo filebeat keystore create
  sudo filebeat keystore add output.elasticsearch.api_key
  ```
  ```yaml
  output.elasticsearch:
    hosts: ["https://10.211.55.63:9200"]
    api_key: ${output.elasticsearch.api_key}
    ssl:
      certificate_authorities: ["/etc/filebeat/certs/ca.crt"]
  ```
- Long‑term: use the cert’s **hostname** (DNS/hosts) rather than relaxing verification.

---

## 10) Troubleshooting checklist
- **No data** → Did you append new lines? Is `Harvester started` present? Are you looking at **Data Streams**, not Indices?
- **x509 / unknown authority** → Wrong CA path or not the issuer → fix `certificate_authorities`.
- **Hostname mismatch** → Use the hostname in the cert’s SAN or temporarily `verification_mode: certificate`.
- **Permissions** → Ensure Filebeat can read `/var/lib/docker/containers/*/*.log`. On non‑root runs, add user to `docker` group or adjust ACLs.
- **Role/privileges** → User must be allowed to write to `logs-*` (e.g., `data_stream_writer`). Test with `elastic` to isolate auth issues.

---

### Done!
Pick Option A for quick wins and a stable baseline; switch to Option B for selective, label‑based collection. Both send logs securely over HTTPS via your internal CA.
