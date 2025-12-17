# 🚨 Kibana SSH Bruteforce Alert – Python Watcher

This repository demonstrates **how to build alerting in Kibana (Basic License)** and trigger **custom actions using Python**, without relying on paid connectors (Email / SMS).

The solution follows this flow:

```
SSH Logs → Filebeat → Elasticsearch → Kibana Rule
                                      ↓
                            Connector (Index Action)
                                      ↓
                           Python Alert Watcher Script
```

---

## 🧠 What Problem Does This Solve?

- Kibana **Basic license** does NOT allow Email / SMS / Slack alerts
- We still need **real alerts** for incidents like:
  - SSH Bruteforce attacks
  - Security events
  - Infrastructure issues

✅ Solution: **Write alerts to an index**, then **handle actions externally** using Python.

---

## 🏗️ Architecture Overview

1. **Filebeat** collects SSH logs
2. **Elasticsearch** stores logs
3. **Kibana Rule** detects SSH bruteforce attempts
4. **Kibana Connector (Index)** writes alert data to a custom index
5. **Python script** watches that index and reacts

---

## 📌 Prerequisites

- Elasticsearch cluster (tested with 3 nodes)
- Kibana (8.x / 9.x)
- Filebeat enabled for SSH logs
- Python 3.8+

Python dependency:
```bash
pip install elasticsearch
```

---

## 🔹 Step 1 – Create Kibana Rule (SSH Bruteforce)

In **Kibana → Stack Management → Rules → Create rule**:

- Rule type: **Elasticsearch query**
- Data view: `filebeat-*`
- Query (KQL example):

```kql
message : "Failed password"
```

- Condition:
  - **WHEN count IS ABOVE 5 FOR THE LAST 2 minutes**

This detects repeated failed SSH logins.

---

## 🔹 Step 2 – Create Connector (Index)

In **Stack Management → Connectors → Create connector**:

- Connector type: **Index**
- Index name:

```text
alerts-ssh-bruteforce
```

### 📄 Document to index (IMPORTANT)

Paste **exactly this JSON**:

```json
{
  "rule_name": "{{rule.name}}",
  "alert_id": "{{alert.id}}",
  "message": "{{context.message}}",
  "@timestamp": "{{date}}"
}
```

Save connector.

---

## 🔹 Step 3 – Attach Connector to Rule

- Edit the SSH Bruteforce rule
- Add **Action**
- Select the **Index connector** created above
- Save rule

Now, **every alert fire creates a document** in:

```
alerts-ssh-bruteforce
```

---

## 🔹 Step 4 – Python Alert Watcher Script

Create file: `watch_kibana_alerts.py`

```python
import time
import os
import re
from elasticsearch import Elasticsearch

# =====================
# CONFIG
# =====================
ES_NODES = [
    "https://10.211.55.69:9200",
    "https://10.211.55.70:9200",
    "https://10.211.55.71:9200",
]

ES_USER = "kibana_admin"
ES_PASS = "StrongKibanaPass123!"

ALERT_INDEX = "alerts-ssh-bruteforce"
CHECK_INTERVAL = 5  # seconds
STATE_FILE = "/tmp/last_alert_id.txt"

# =====================
# Elasticsearch Client
# =====================
es = Elasticsearch(
    ES_NODES,
    basic_auth=(ES_USER, ES_PASS),
    verify_certs=False
)

# =====================
# Helper functions
# =====================
def get_last_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_seen(alert_id):
    with open(STATE_FILE, "w") as f:
        f.write(alert_id)

def get_latest_alert():
    res = es.search(
        index=ALERT_INDEX,
        size=1,
        sort=[{"@timestamp": {"order": "desc"}}],
        _source=["rule_name", "message", "count", "match_count", "host_ip", "@timestamp"]
    )
    hits = res["hits"]["hits"]
    return hits[0] if hits else None

def extract_count_from_message(msg: str):
    # مثال message شما: "Document count is 3 in the last 1m ..."
    m = re.search(r"Document count is\s+(\d+)", msg or "")
    return int(m.group(1)) if m else None

# =====================
# Main loop
# =====================
print("🚀 Kibana Alert Watcher started")
last_seen = get_last_seen()

while True:
    try:
        alert = get_latest_alert()
        if not alert:
            time.sleep(CHECK_INTERVAL)
            continue

        alert_id = alert["_id"]

        if alert_id != last_seen:
            src = alert["_source"]

            # اولویت با فیلدی که خودت ذخیره کردی:
            count = src.get("count")
            if not count:
                count = src.get("match_count")

            # اگر باز هم نبود، از message استخراج کن:
            if not count:
                count = extract_count_from_message(src.get("message"))

            print("\n" + "="*50)
            print("🚨 ALERT TRIGGERED")
            print(f"Rule Name : {src.get('rule_name')}")
            print(f"Message   : {src.get('message')}")
            print(f"Count     : {count}")
            print(f"Host IP   : {src.get('host_ip')}")
            print(f"Time      : {src.get('@timestamp')}")
            print("="*50)

            save_last_seen(alert_id)
            last_seen = alert_id

        time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
        break
    except Exception as e:
        print("❌ Error:", e)
        time.sleep(CHECK_INTERVAL)
```

---

## 🔹 Step 5 – Run & Test

### Run script
```bash
python3 watch_kibana_alerts.py
```

### Simulate SSH bruteforce
```bash
ssh fakeuser@10.211.55.69
ssh fakeuser@10.211.55.69
ssh fakeuser@10.211.55.69
```

### Expected output
```text
🚨 ALERT TRIGGERED
Rule Name : SSH Bruteforce Attack
Message   : Failed password detected
Count     : 5
Time      : 2025-12-17T10:12:01Z
```

---

## 🚀 Next Enhancements

This setup can easily be extended to:

- Telegram bot notifications
- Email alerts
- Webhooks
- systemd service
- Docker container

---

## ✅ Summary

- Kibana Basic license **is enough** for real alerting
- Index connector is the key workaround
- Python gives full control over alert actions

Happy monitoring 🔥

