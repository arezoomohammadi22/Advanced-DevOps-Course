# NGINX → Syslog → Logstash Minimal Pipeline

This README describes the working configuration for sending **NGINX logs** from a web server to a **central rsyslog server**, which stores them locally and forwards them to a **Logstash instance** running from a tar.gz installation.

---

## 🧩 Topology Overview

| Role | Hostname | IP Address | Description |
|------|-----------|-------------|--------------|
| **NGINX Web Server** | lab-node02 | 10.211.55.64 | Sends access/error logs to syslog server via UDP/514 |
| **Syslog Server (rsyslog)** | lab-node03 | 10.211.55.65 | Receives UDP/514 logs, stores locally, and forwards via TCP/5000 to Logstash |
| **Logstash Server** | lab-node01 | 10.211.55.63 | Receives forwarded logs and prints to console |

---

## ⚙️ Syslog Server Configuration (lab-node03)

**File:** `/etc/rsyslog.d/10-nginx.conf`

```conf
# /etc/rsyslog.d/10-nginx.conf

# listen on UDP/514 with a dedicated ruleset
module(load="imudp")
input(type="imudp" port="514" ruleset="nginx_in")

# sane default modes for files/dirs created by this process
$DirCreateMode 0755
$FileCreateMode 0644

# define a reliable action queue for the forwarder
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
}
```

### Apply configuration
```bash
sudo mkdir -p /var/log/remote /var/spool/rsyslog
sudo chown syslog:adm /var/log/remote
sudo systemctl restart rsyslog
sudo journalctl -u rsyslog -n 50 --no-pager
```

### Verification
```bash
ss -lun | grep :514     # confirm UDP listener
sudo tcpdump -ni any udp port 514 -vv  # ensure packets from NGINX arrive
```

---

## 📦 Logstash Configuration (lab-node01)

**Installation:** Logstash 9.1.4 (tar.gz, ARM)

**Pipeline file:** `pipelines/syslog-nginx.conf`

```conf
input {
  tcp {
    host  => "0.0.0.0"   # listen on all interfaces
    port  => 5000
    codec => plain        # receive plain text syslog lines
    type  => "syslog_raw"
  }
}

filter { }

output {
  stdout { codec => rubydebug }
}
```

### Validate and Run Logstash
```bash
cd ~/logstash-9.1.4
./bin/logstash --config.test_and_exit -f pipelines/syslog-nginx.conf
./bin/logstash -f pipelines/syslog-nginx.conf
```

### Verification
On the Logstash node:
```bash
ss -ltnp | grep :5000        # confirm Logstash is listening
sudo tcpdump -ni any tcp port 5000 -vv   # confirm rsyslog is forwarding
```

You should see rubydebug events printed in the Logstash console.

---

## 🌐 NGINX Configuration (lab-node02)

**Inside `/etc/nginx/nginx.conf` → http block:**

```nginx
log_format main '$remote_addr - $remote_user [$time_local] '
                '"$request" $status $body_bytes_sent '
                '"$http_referer" "$http_user_agent"';

access_log syslog:server=10.211.55.65:514,facility=local7,tag=nginx,severity=info main;
error_log syslog:server=10.211.55.65:514,facility=local7,tag=nginx_error warn;
```

### Test and Reload
```bash
nginx -t && systemctl reload nginx
```

Generate sample traffic:
```bash
for i in {1..20}; do curl -s http://10.211.55.64/ >/dev/null; done
```

---

## 🔍 End-to-End Flow Verification

1. **Syslog Server (lab-node03)**
   ```bash
   tail -n2 /var/log/remote/remote-catchall.log /var/log/remote/nginx-from-syslog.log
   sudo tcpdump -ni any tcp port 5000 -vv   # verify forward to Logstash
   ```

2. **Logstash Server (lab-node01)**
   ```bash
   ss -ltnp | grep :5000
   ./bin/logstash -f pipelines/syslog-nginx.conf   # watch rubydebug output
   ```

3. **Expected Logstash Output:**
   ```json
   {
     "message" => "<14>1 2025-11-03T18:35:12Z lab-node02 nginx: 10.211.55.64 - - [03/Nov/2025:18:35:12 +0330] \"GET / HTTP/1.1\" 200 612 \"-\" \"curl/7.81.0\"",
     "@version" => "1",
     "@timestamp" => 2025-11-03T18:35:12.000Z,
     "type" => "syslog_raw",
     "host" => "10.211.55.63"
   }
   ```

---

## ✅ Success Criteria
- `rsyslog` receives UDP traffic from NGINX (`remote-catchall.log` grows)
- `rsyslog` forwards over TCP/5000 to Logstash
- `Logstash` displays rubydebug events containing syslog lines

Once verified, you can extend the pipeline with `grok` filters and an Elasticsearch output.

---

## 🧹 Troubleshooting

| Issue | Check |
|-------|--------|
| No events in Logstash | Run `tcpdump` on both nodes, check firewall and ports |
| Logstash not listening | Run `ss -ltnp | grep 5000` |
| rsyslog queueing messages | Look in `/var/spool/rsyslog` |
| Permission denied writing logs | `chown syslog:adm /var/log/remote` |
| NGINX not logging | Run `nginx -T` and generate traffic manually |

---

## 🧱 Next Steps
- Add a `grok` filter in Logstash to parse NGINX fields.
- Enable Elasticsearch output for persistent storage and dashboards.
- Visualize in Kibana or Grafana.

---

**Author:** Arezoo  
**Version:** 1.0  
**Date:** 2025-11-03

