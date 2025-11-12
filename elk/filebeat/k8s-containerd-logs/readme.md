# 📘 Filebeat → Elasticsearch (Custom Data Stream Configuration)

## 🧩 Overview
This setup sends logs from your local path or containers to **Elasticsearch** securely over HTTPS.  
It uses **Filebeat** with a **custom data stream name**, instead of the default `filebeat-9.x` pattern.

---

## ⚙️ Prerequisites
- Elasticsearch 8.x or 9.x running and reachable via HTTPS  
- Valid Elasticsearch credentials or API key  
- SSL certificate (`ca.crt`) of Elasticsearch cluster  
- Filebeat installed (matching your ES version)

---

## 🪶 Configuration Steps

### 1️⃣ Edit `filebeat.yml`
Example minimal configuration:

```yaml
filebeat.inputs:
  - type: filestream
    id: app-logs
    enabled: true
    paths:
      - /var/log/myapp/*.log
    fields:
      app: "myapp"
      env: "prod"

processors:
  - add_host_metadata: ~
  - add_cloud_metadata: ~
  - add_fields:
      target: ""
      fields:
        data_stream.dataset: "myapp"
        data_stream.type: "logs"
        data_stream.namespace: "prod"

output.elasticsearch:
  hosts: ["https://elasticsearch.example.com:9200"]
  protocol: "https"
  ssl.certificate_authorities: ["/etc/filebeat/certs/ca.crt"]
  username: "elastic"
  password: "YourPassword"

  # ✅ Custom data stream name
  index: "logs-myapp-prod"

setup.template.name: "logs-myapp-prod"
setup.template.pattern: "logs-myapp-prod*"
setup.ilm.enabled: false
```

---

### 2️⃣ Create SSL Connection Test
Before running Filebeat, confirm SSL connectivity:

```bash
curl -v --cacert /etc/filebeat/certs/ca.crt https://elasticsearch.example.com:9200
```

Expected output:
```bash
{
  "name" : "es-node01",
  "cluster_name" : "my-es-cluster",
  "version" : { "number" : "9.2.0" },
  "tagline" : "You Know, for Search"
}
```

---

### 3️⃣ Enable and Start Filebeat

```bash
sudo filebeat test output
sudo systemctl enable filebeat
sudo systemctl start filebeat
sudo systemctl status filebeat
```

If you prefer to run manually:
```bash
sudo filebeat -e -c /etc/filebeat/filebeat.yml
```

---

### 4️⃣ Verify Data Stream in Elasticsearch
```bash
curl -X GET -u elastic:YourPassword https://elasticsearch.example.com:9200/_data_stream?pretty
```

Expected result:
```json
{
  "data_streams" : [
    {
      "name" : "logs-myapp-prod",
      "timestamp_field" : { "name" : "@timestamp" },
      "indices" : [...]
    }
  ]
}
```

---

### 5️⃣ View Logs in Kibana
1. Go to **Stack Management → Data Streams**
2. Find `logs-myapp-prod`
3. Use **Discover** to view incoming logs

---

## 🔁 Optional: Route Multiple Inputs
You can route different modules or log sources to separate streams:

```yaml
output.elasticsearch:
  indices:
    - index: "logs-nginx-prod"
      when.contains:
        fileset.module: "nginx"
    - index: "logs-app-prod"
      when.equals:
        fields.app: "myapp"
```

---

## 🧰 Useful Commands

| Action | Command |
|--------|----------|
| Test config syntax | `filebeat test config -c filebeat.yml` |
| Test ES output | `filebeat test output` |
| Debug Filebeat | `filebeat -e -d "*" -c filebeat.yml` |
| List modules | `filebeat modules list` |

---

## 📄 Log File
Default Filebeat logs:
```bash
sudo tail -f /var/log/filebeat/filebeat
```
or define your own in `/etc/filebeat/filebeat.yml`:
```yaml
logging.to_files: true
logging.files:
  path: /var/log/filebeat
  name: filebeat
  keepfiles: 7
  permissions: 0644
```

---

## 🧠 Notes
- You **cannot rename** an existing data stream; create a new one instead.  
- For existing data, use `_reindex` API to migrate old indices to new stream.  
- Always restart Filebeat after config changes:
  ```bash
  sudo systemctl restart filebeat
  ```

---

## ✅ Example: For Loop to Monitor Logs
If you want to continuously test and send logs:
```bash
for i in {1..10}; do
  echo "$(date) Test log $i" >> /var/log/myapp/test.log
  sleep 2
done
```

---

**Author:** Arezoo Mohammadi  
**Version:** Filebeat 9.2.x  
**License:** Apache 2.0  
**Website:** [https://sananetco.com](https://sananetco.com)
