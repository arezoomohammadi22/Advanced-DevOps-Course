# NGINX ➔ Syslog Server ➔ Logstash Lab

This lab guides you through setting up an end-to-end logging pipeline:

```
NGINX (web-01)  --->  rsyslog (syslog-01)  --->  Logstash (logstash-01)
```

The goal is to send NGINX access and error logs to a central syslog server via UDP (port 514), store them locally, and later forward them to Logstash for parsing and analysis.

---

## 🧱 Prerequisites

| Host | Role | Example IP |
|------|------|-------------|
| web-01 | NGINX web server | 10.211.55.64 |
| syslog-01 | rsyslog server | 10.211.55.65 |
| logstash-01 | Logstash server | 10.211.55.66 |

---

## ⚙️ Step 1: Install and Configure Syslog Server

### 1. Install rsyslog

On **syslog-01**:

```bash
sudo apt update
sudo apt install -y rsyslog
sudo systemctl enable --now rsyslog
```

### 2. Prepare a log directory

```bash
sudo mkdir -p /var/log/remote
sudo chown syslog:adm /var/log/remote
sudo chmod 0755 /var/log/remote
```

### 3. Configure rsyslog for UDP input

Create `/etc/rsyslog.d/10-nginx.conf`:

```conf
# listen on UDP/514 with a dedicated ruleset
module(load="imudp")
input(type="imudp" port="514" ruleset="nginx_in")

# sane default modes for files/dirs created by this process
$DirCreateMode 0755
$FileCreateMode 0644

ruleset(name="nginx_in") {
  # catch-all: prove ingestion first
  action(type="omfile" File="/var/log/remote/remote-catchall.log")

  # nginx-specific copy
  if ($programname == "nginx") or ($syslogtag startswith "nginx") then {
    action(type="omfile" File="/var/log/remote/nginx-from-syslog.log")
    stop
  }
}
```

### 4. Validate and restart rsyslog

```bash
sudo rsyslogd -N1   # validate configuration syntax
sudo systemctl restart rsyslog
sudo journalctl -u rsyslog -n 50 --no-pager
```

You should see no errors.

---

## 🌐 Step 2: Configure NGINX to Send Logs to Syslog

On **web-01**:

### 1. Install NGINX

```bash
sudo apt update
sudo apt install -y nginx
sudo systemctl enable --now nginx
```

### 2. Edit `/etc/nginx/nginx.conf`

Inside the `http {}` block:

```nginx
log_format main '$remote_addr - $remote_user [$time_local] '
                '"$request" $status $body_bytes_sent '
                '"$http_referer" "$http_user_agent"';

# Send access logs to syslog server over UDP 514
access_log syslog:server=10.211.55.65:514,facility=local7,tag=nginx,severity=info main;

# Also ship error log lines to syslog
error_log syslog:server=10.211.55.65:514,facility=local7,tag=nginx_error warn;
```

Validate and reload:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### 3. Generate some traffic

```bash
for i in {1..20}; do curl -s http://10.211.55.64/ >/dev/null; done
```

---

## 🧪 Step 3: Verify Logs on Syslog Server

On **syslog-01**:

### 1. Confirm UDP listener
```bash
sudo ss -lun | grep ':514 '
```

### 2. Monitor log files
```bash
sudo tail -f /var/log/remote/remote-catchall.log /var/log/remote/nginx-from-syslog.log
```

You should now see entries similar to:

```
<13>1 2025-11-03T18:37:01 lab-node02 nginx - - - 10.211.55.64 - - [03/Nov/2025:18:36:59 +0330] "GET / HTTP/1.1" 200 612 "-" "curl/7.81.0"
```

### 3. Optional debugging
If needed, use:
```bash
sudo tcpdump -ni any udp port 514 -vv
```
Or test manually from NGINX:
```bash
logger -n 10.211.55.65 -P 514 -d "hello from logger over UDP"
```

---

## 🧹 Step 4: Troubleshooting Commands

```bash
sudo rsyslogd -N1                    # validate syntax
sudo journalctl -u rsyslog -n 50     # check service logs
sudo tail -f /var/log/remote/*.log   # monitor incoming logs
sudo tcpdump -ni any udp port 514 -vv # sniff incoming UDP packets
```

If you see "omfile suspended" messages, verify file permissions:
```bash
sudo chown syslog:adm /var/log/remote
sudo chmod 0755 /var/log/remote
```

---

## ✅ Verification Summary
| Check | Command | Expected |
|--------|----------|-----------|
| rsyslog listening | `ss -lun | grep 514` | Shows UDP/514 bound |
| packets arriving | `tcpdump -ni any udp port 514 -vv` | Incoming SYSLOG packets |
| logs written | `tail -f /var/log/remote/*.log` | NGINX log lines appear |
| manual test | `logger -n <syslog_ip> -P 514 -d "test"` | Message in remote-catchall.log |
