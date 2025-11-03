# NGINX → rsyslog → Logstash → Elasticsearch (Minimal, Tested)

This README captures your **working configs** to forward NGINX logs to a central rsyslog server, then on to Logstash, and finally index them in **Elasticsearch** (with Kibana data view).

---

## 🧩 Topology

| Role | Host | IP | Notes |
|---|---|---|---|
| NGINX | lab-node02 | 10.211.55.64 | Ships access/error logs to rsyslog (UDP/514) |
| rsyslog | lab-node03 | 10.211.55.65 | Receives UDP/514; stores + forwards TCP/5000 to Logstash |
| Logstash + Elasticsearch | lab-node01 | 10.211.55.63 | Logstash (tar.gz, ARM) listens on TCP/5000; outputs to local Elasticsearch over HTTPS:9200 |

---

## ✅ Prerequisites
- NGINX configured to send logs to rsyslog (from previous step).
- rsyslog installed and enabled on **lab-node03**.
- Logstash 9.1.4 (tar.gz, ARM) unpacked on **lab-node01**.
- Elasticsearch running on **lab-node01:9200** (HTTPS) with a user that can write to `syslog-raw-*`.

> **Security note:** Current Logstash output disables TLS verification (`ssl_verification_mode => none`) while also supplying a CA file. Prefer using a valid CA and enabling verification for non-lab use.

---

## 1) rsyslog configuration (lab-node03)

**File:** `/etc/rsyslog.d/10-nginx.conf`

```conf
# /etc/rsyslog.d/10-nginx.conf

# listen on UDP/514 with a dedicated ruleset
module(load="imudp")
input(type="imudp" port="514" ruleset="nginx_in")

# sane default modes for files/dirs created by this process
$DirCreateMode 0755
$FileCreateMode 0644

# (optional but recommended) define a reliable action queue for the forwarder
$WorkDirectory /var/spool/rsyslog
$ActionQueueType LinkedList
$ActionQueueFileName fwd_to_logstash
$ActionQueueMaxDiskSpace 100m
$ActionResumeRetryCount -1   # retry forever

ruleset(name="nginx_in") {
  # catch-all: prove ingestion first
  action(type="omfile" File="/var/log/remote/remote-catchall.log")

  # nginx-specific: write locally AND forward to logstash, then stop
  if ($programname == "nginx") or ($syslogtag startswith "nginx") then {
    # local copy
    action(type="omfile" File="/var/log/remote/nginx-from-syslog.log")

    # forward to Logstash over TCP/5000 using RFC5424 format
    action(type="omfwd"
           target="10.211.55.63"
           port="5000"
           protocol="tcp"
           template="RSYSLOG_SyslogProtocol23Format"
           keepalive="on")

    stop
  }

  # (optional) forward EVERYTHING instead of only nginx
  # action(type="omfwd" target="10.211.55.63" port="5000" protocol="tcp"
  #        template="RSYSLOG_SyslogProtocol23Format" keepalive="on")
}

# --- OPTIONAL (RELP, more reliable than TCP) ---
# module(load="omrelp")
# action(type="omrelp" target="10.211.55.63" port="5514")
```

Apply & verify:
```bash
sudo mkdir -p /var/log/remote /var/spool/rsyslog
sudo chown syslog:adm /var/log/remote || true
sudo systemctl restart rsyslog
ss -lun | grep :514
sudo tail -n2 /var/log/remote/remote-catchall.log /var/log/remote/nginx-from-syslog.log
```

---

## 2) Logstash pipeline (lab-node01)

**File:** `~/logstash-9.1.4/pipelines/syslog-nginx.conf`

```conf
input {
  tcp {
    host  => "0.0.0.0"   # optional; listen on all interfaces
    port  => 5000
    codec => plain       # or just omit; default is plain
    type  => "syslog_raw"
  }
}

filter { }

output {
  elasticsearch {
    hosts  => ["https://10.211.55.63:9200"]   # ES reachable at :9200
    index  => "syslog-raw-%{+YYYY.MM.dd}"

    # TLS settings (lab-friendly)
    ssl_enabled => true
    ssl_verification_mode => none            # disables cert verification (lab)
    ssl_certificate_authorities => ["/home/arezoo/cert/cacert.pem"]

    # Auth via env vars
    user     => "${ES_USER}"
    password => "${ES_PASSWORD}"
  }

  # Keep console visibility while testing
  stdout { codec => rubydebug }
}
```

Set credentials (current session):
```bash
export ES_USER="logstash_writer"
export ES_PASSWORD="your_strong_password"
```

Validate & run:
```bash
cd ~/logstash-9.1.4
./bin/logstash --config.test_and_exit -f pipelines/syslog-nginx.conf
./bin/logstash -f pipelines/syslog-nginx.conf
```

Quick checks on lab-node01:
```bash
ss -ltnp | grep :5000               # Logstash listening
sudo tcpdump -ni any tcp port 5000 -vv  # packets from rsyslog
```

Generate NGINX traffic on lab-node02:
```bash
for i in {1..30}; do curl -s http://10.211.55.64/ >/dev/null; done
```

---

## 3) Elasticsearch index & Kibana data view

> With the config above, **indices are auto-created** on first write (e.g., `syslog-raw-2025.11.03`). You can verify and then create a Kibana data view to explore.

### Verify index in Elasticsearch
```bash
# adjust auth/URL flags to your cluster
curl -k -u "$ES_USER:$ES_PASSWORD" "https://10.211.55.63:9200/_cat/indices/syslog-raw-*?v"

# count docs
curl -k -u "$ES_USER:$ES_PASSWORD" "https://10.211.55.63:9200/syslog-raw-*/_count?pretty"
```

### Create a Kibana Data View (UI)
1. Open **Kibana → Stack Management → Data Views**
2. **Create data view**
   - **Name:** `syslog-raw`
   - **Index pattern:** `syslog-raw-*`
   - **Time field:** `@timestamp`
3. Save, then go to **Discover** and select the `syslog-raw` data view.

> Tip: If no documents appear yet, generate NGINX traffic again and refresh Discover.

---

## 4) End-to-End Smoke Test

On rsyslog (lab-node03):
```bash
sudo tail -n2 /var/log/remote/nginx-from-syslog.log
sudo tcpdump -ni any tcp port 5000 -vv
```
On Logstash (lab-node01):
```bash
./bin/logstash -f pipelines/syslog-nginx.conf   # watch rubydebug events
```
On Elasticsearch:
```bash
curl -k -u "$ES_USER:$ES_PASSWORD" "https://10.211.55.63:9200/_cat/indices/syslog-raw-*?v"
```
In Kibana:
- Data View `syslog-raw` exists
- Discover shows incoming docs

---

## 🔧 Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| No docs in ES but Logstash prints events | ES URL/auth/TLS mismatch | Check `hosts`, creds, and TLS flags; try `curl` with `-k` and same user/pass |
| Logstash not listening on 5000 | Config error or wrong path | Run `--config.test_and_exit`; ensure you start the same file |
| rsyslog not forwarding | Forward action or firewall | Verify `/etc/rsyslog.d/10-nginx.conf`, restart rsyslog, `tcpdump` 5000 |
| TLS errors | Self-signed CA or disabled verification | Use correct CA file and enable verification (recommended), or keep lab flags |
| Permission denied writing rsyslog files | Ownership/permissions | `chown syslog:adm /var/log/remote` and `chmod 755` |

---


