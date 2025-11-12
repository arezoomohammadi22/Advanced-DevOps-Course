# Filebeat + TLS (Internal CA) — Quick Setup (Debian package)

This guide configures Filebeat to read a local log file and ship events securely to **Elasticsearch over HTTPS** using your **internal CA**. It also includes commands to verify TLS with `curl`, create and grow a test log, and validate ingestion.

> Assumptions  
> - You installed Filebeat via the Debian package (`apt`) and it runs as a systemd service.  
> - Default paths:  
>   - Config: `/etc/filebeat/filebeat.yml`  
>   - Data: `/var/lib/filebeat`  
>   - Logs: `/var/log/filebeat`  
> - Elasticsearch listens on **HTTPS**.  
> - You have the **root CA** (or chain) that signed your Elasticsearch cert.

---

## 1) Place your internal CA on the Filebeat host

Copy your CA file (PEM) to a readable path, e.g.:

```bash
sudo mkdir -p /etc/filebeat/certs
sudo cp ~/cacert.pem /etc/filebeat/certs/ca.crt
sudo chown root:root /etc/filebeat/certs/ca.crt
sudo chmod 0644 /etc/filebeat/certs/ca.crt
```

> Ensure this **is the CA** that signed the Elasticsearch server certificate (not the server certificate itself).

---

## 2) Verify TLS to Elasticsearch with `curl`

Replace values as appropriate:

```bash
ES_HOST="10.211.55.63"
ES_PORT="9200"
ES_USER="sananet"
ES_PASS="123456"
CA_FILE="/etc/filebeat/certs/ca.crt"

curl -s --cacert "$CA_FILE" -u "$ES_USER:$ES_PASS" "https://$ES_HOST:$ES_PORT"
```

- If you see a JSON response with Elasticsearch cluster details, TLS and auth are OK.
- If you get a **hostname mismatch** but need to use an **IP** (not the hostname in the cert SAN), you can either fix DNS/hosts to use the proper hostname **(recommended)** or temporarily relax verification in Filebeat (see below).

---

## 3) Configure Filebeat input + TLS output

Edit `/etc/filebeat/filebeat.yml` and use this minimal, clean config. Adjust paths and credentials:

```yaml
filebeat.inputs:
  - type: filestream
    id: my-filestream-id
    enabled: true
    paths:
      - /root/file01.log

    # OPTIONAL: allow ingesting small log files (< 1KB)
    prospector.scanner.fingerprint.length: 256
    prospector.scanner.fingerprint.offset: 0

    # OPTIONAL but recommended for discoverability in Kibana (Data Streams)
    data_stream.dataset: "myapp"
    data_stream.namespace: "prod"

filebeat.config.modules:
  path: ${path.config}/modules.d/*.yml
  reload.enabled: false

setup.template.settings:
  index.number_of_shards: 1

# ---- Elasticsearch HTTPS output with internal CA ----
output.elasticsearch:
  hosts: ["https://10.211.55.63:9200"]
  username: "sananet"
  password: "123456"

  ssl:
    certificate_authorities: ["/etc/filebeat/certs/ca.crt"]
    # If you're connecting via IP but the cert is issued for a hostname,
    # you can temporarily relax hostname verification (NOT a long-term fix):
    # verification_mode: certificate

# Keep processors empty during first validation to avoid surprises
processors: []
```

> **Security tip**: Instead of placing credentials in plain text, consider using the Filebeat keystore:
> ```bash
> sudo filebeat keystore create
> sudo filebeat keystore add output.elasticsearch.username
> sudo filebeat keystore add output.elasticsearch.password
> ```
> Then change in `filebeat.yml`:
> ```yaml
> output.elasticsearch:
>   hosts: ["https://10.211.55.63:9200"]
>   username: ${output.elasticsearch.username}
>   password: ${output.elasticsearch.password}
>   ssl:
>     certificate_authorities: ["/etc/filebeat/certs/ca.crt"]
> ```

---

## 4) Validate Filebeat configuration and connection

```bash
sudo filebeat test config -e
sudo filebeat test output -e
```

- `test config` should print `Config OK`.
- `test output` should say it can **talk to Elasticsearch**; otherwise you’ll see a clear TLS/auth error to fix.

---

## 5) Create the log file and add lines

If the file doesn’t exist yet:

```bash
sudo bash -c 'echo "$(date -Is) initial log line" > /root/file01.log'
```

To **grow the file above 1KB** (Filebeat’s default fingerprint size is 1024 bytes), append ~80 lines:

```bash
for i in {1..80}; do
  echo "$(date -Is) filebeat test line $i" | sudo tee -a /root/file01.log >/dev/null
done
```

> If you used the `prospector.scanner.fingerprint.length: 256` in the config, small files will be ingested as well.

---

## 6) Restart Filebeat and inspect its logs

```bash
sudo systemctl restart filebeat
sudo journalctl -u filebeat -n 200 --no-pager
```

Look for messages like:
- `Connected to Elasticsearch`
- `Harvester started for file: /root/file01.log`

---

## 7) Confirm data in Elasticsearch (Data Streams)

Filebeat 8/9 writes to **Data Streams** by default. Check via API:

```bash
curl -s --cacert "$CA_FILE" -u "$ES_USER:$ES_PASS" "https://$ES_HOST:$ES_PORT/_data_stream?pretty"
```

You should see something like:
- `logs-generic-default` (if you didn’t set dataset/namespace), or
- `logs-myapp-prod` (if you used the values from the example).

In Kibana, go to: **Stack Management → Data Streams** and locate your stream. Use Discover to query it.

---

## 8) Common pitfalls & quick fixes

- **Nothing shows up** → Ensure a **new line** was appended to the log after Filebeat started; confirm `Harvester started` in Filebeat logs.
- **x509/unknown authority** → CA path is wrong or not the issuer; fix `ssl.certificate_authorities` and re-run `test output`.
- **Hostname mismatch** → Use the hostname present in the cert’s SAN, or temporarily set `verification_mode: certificate` until DNS/hosts is fixed.
- **Permission denied reading `/root/file01.log`** → The service runs as root by default on Debian packages; if you changed the user, either adjust perms or move the log to `/var/log/myapp/file01.log` and update `paths`.

---

## 9) Optional: Foreground run for troubleshooting

```bash
sudo systemctl stop filebeat
sudo /usr/share/filebeat/bin/filebeat -e -c /etc/filebeat/filebeat.yml
```

Press `Ctrl+C` to stop, then:
```bash
sudo systemctl start filebeat
```

---

### Done!
You now have a secure Filebeat → Elasticsearch pipeline over HTTPS with an internal CA, validated with `curl`, and a test log producing events.
