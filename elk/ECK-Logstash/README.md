# Install Logstash on Kubernetes using ECK (Elastic Cloud on Kubernetes)

This guide explains how to install **Logstash on a Kubernetes cluster using ECK** based on the exact manifests you provided:
- `Logstash` custom resource
- `pipelinesRef` using a Secret
- Beats input on port `5044`
- Secure connection to Elasticsearch via `elasticsearchRefs`

---

## Prerequisites

- Kubernetes cluster up and running
- `kubectl` access with admin permissions
- **ECK operator installed**
- An existing Elasticsearch cluster managed by ECK  
  (in this guide it is named **es-logging**)

---

## 1) Install ECK Operator (skip if already installed)

```bash
kubectl create -f https://download.elastic.co/downloads/eck/2.11.0/crds.yaml
kubectl apply  -f https://download.elastic.co/downloads/eck/2.11.0/operator.yaml
```

Verify:

```bash
kubectl get pods -n elastic-system
```

---

## 2) Create Logstash Pipeline Secret

Logstash pipelines are referenced via `pipelinesRef`, which must point to a Secret
containing `pipelines.yml`.

### `logstash-pipeline-secret.yaml`

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: logstash-pipeline
  namespace: default
stringData:
  pipelines.yml: |-
    - pipeline.id: main
      config.string: |
        input {
          beats {
            port => 5044
          }
        }

        output {
          elasticsearch {
            hosts => [ "${ES_LOGGING_ES_HOSTS}" ]
            user => "${ES_LOGGING_ES_USER}"
            password => "${ES_LOGGING_ES_PASSWORD}"
            ssl_certificate_authorities => "${ES_LOGGING_ES_SSL_CERTIFICATE_AUTHORITY}"
            index => "beats-%{+YYYY.MM.dd}"
          }

          stdout {
            codec => rubydebug
          }
        }
```

Apply it:

```bash
kubectl apply -f logstash-pipeline-secret.yaml
```

---

## 3) Create Logstash Custom Resource (ECK)

⚠️ **Important:**  
Do **not** mix different Logstash versions.  
Your original manifest had:
- `version: 8.12.2`
- `image: logstash:9.2.2`

This is **not recommended**.  
ECK expects the Logstash image to match the declared version.

### Recommended approach
Let ECK select the correct image by **removing `image:`**.

### `logstash.yaml`

```yaml
apiVersion: logstash.k8s.elastic.co/v1alpha1
kind: Logstash
metadata:
  name: logstash-logging
  namespace: default
spec:
  version: 8.12.2
  count: 1

  elasticsearchRefs:
    - name: es-logging
      clusterName: es-logging

  pipelinesRef:
    secretName: logstash-pipeline
```

Apply it:

```bash
kubectl apply -f logstash.yaml
```

---

## 4) Expose Logstash Beats Port (5044)

Your pipeline listens on port `5044`.  
You must expose it with a Kubernetes Service so Filebeat / Beats can connect.

### `logstash-service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: logstash-logging-beats
  namespace: default
spec:
  selector:
    logstash.k8s.elastic.co/name: logstash-logging
  ports:
    - name: beats
      port: 5044
      targetPort: 5044
  type: ClusterIP
```

Apply it:

```bash
kubectl apply -f logstash-service.yaml
```

Beats endpoint:

```
logstash-logging-beats.default.svc:5044
```

---

## 5) How Elasticsearch Credentials Work (Important)

Because you used:

```yaml
elasticsearchRefs:
  - name: es-logging
    clusterName: es-logging
```

ECK automatically injects these environment variables into Logstash:

- `ES_LOGGING_ES_HOSTS`
- `ES_LOGGING_ES_USER`
- `ES_LOGGING_ES_PASSWORD`
- `ES_LOGGING_ES_SSL_CERTIFICATE_AUTHORITY`

These are exactly what you referenced in your pipeline configuration.

✅ No manual secret wiring needed.

---

## 6) Verify Installation

```bash
kubectl get logstash logstash-logging
kubectl get pods -l logstash.k8s.elastic.co/name=logstash-logging
kubectl logs -f deploy/logstash-logging
kubectl get svc logstash-logging-beats
```

If Logstash fails to start, check logs for:
- Missing env vars
- Elasticsearch authentication errors
- Pipeline syntax errors

---

## 7) Example Filebeat Output (for testing)

```yaml
output.logstash:
  hosts: ["logstash-logging-beats.default.svc:5044"]
```

---

## 8) Common Troubleshooting

### Logstash pod CrashLoopBackOff
- Version mismatch (image vs version)
- Invalid pipeline syntax
- Missing Elasticsearch reference

### Filebeat cannot connect
- Service not created
- Wrong namespace
- NetworkPolicy blocking traffic

### Elasticsearch index not created
- Logstash user lacks index privileges
- SSL CA variable missing

---

## Summary

You installed Logstash on Kubernetes using:
- ✅ ECK Logstash CR
- ✅ pipelinesRef with Secret
- ✅ Secure Elasticsearch connection
- ✅ Beats input via ClusterIP Service

This setup is production-ready and fully aligned with Elastic best practices.

---

Happy logging 🚀
