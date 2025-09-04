
# NGINX Client Body Size & Buffer Testing

This guide demonstrates how to test and simulate NGINX's handling of HTTP request body limits using the `client_max_body_size` and `client_body_buffer_size` directives.

---

## 📌 Goal

Simulate large POST requests and observe how NGINX:

- Accepts small requests in memory
- Stores medium requests in temp files
- Rejects oversized bodies with `413 Request Entity Too Large`

---

## ⚙️ NGINX Configuration

```nginx
server {
    listen 80;
    server_name test.local;

    client_body_buffer_size 1k;   # In-memory buffer size
    client_max_body_size 4k;      # Max POST body size

    error_page 413 /error413;
    location = /error413 {
        return 413 "❌ File too large. Limit is 4 KB.\n";
    }

    location /upload {
        proxy_pass http://127.0.0.1:3000;
        add_header X-Limit-Test "upload-handled";
    }
}
```

Reload NGINX:

```bash
sudo nginx -t && sudo nginx -s reload
```

> Make sure `127.0.0.1 test.local` exists in `/etc/hosts`.

---

## 🧬 Python Backend for /upload

```python
from http.server import BaseHTTPRequestHandler, HTTPServer

class SimpleUploadHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        print(f"Received {len(body)} bytes")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Upload received.")

server = HTTPServer(('0.0.0.0', 3000), SimpleUploadHandler)
print("Listening on port 3000...")
server.serve_forever()
```

Run the backend:

```bash
python3 upload_server.py
```

---

## 📦 Step 1: Create Test Files

```bash
# Small payload (2 KB)
head -c 2048 /dev/urandom > small_payload.bin

# Large payload (8 KB)
head -c 8192 /dev/urandom > large_payload.bin
```

---

## 📤 Step 2: Test with curl

### ✅ Small Upload (Passes)

```bash
curl -X POST http://test.local/upload   -H "Content-Type: application/octet-stream"   --data-binary @small_payload.bin -v
```

Expected:
```
HTTP/1.1 200 OK
X-Limit-Test: upload-handled
```

### ❌ Large Upload (Fails)

```bash
curl -X POST http://test.local/upload   -H "Content-Type: application/octet-stream"   --data-binary @large_payload.bin -v
```

Expected:
```
HTTP/1.1 413 Request Entity Too Large
❌ File too large. Limit is 4 KB.
```

---

## 🧠 What Happens Internally

| Request Size      | Behavior                       |
|-------------------|--------------------------------|
| ≤ 1 KB            | Stored in memory               |
| > 1 KB, ≤ 4 KB    | Stored to temp file            |
| > 4 KB            | Rejected with 413              |

Temp files go to: `/var/lib/nginx/body/` or `client_body_temp_path`

---

## 🧪 Troubleshooting

- Check logs:

```bash
tail -f /usr/local/nginx/logs/error.log
```

- Use custom headers to verify config is applied:

```nginx
add_header X-Debug "Upload Block Matched";
```

---

## ✅ Summary

- `client_max_body_size` blocks large POST requests
- `client_body_buffer_size` controls memory vs disk usage
- 413 status means rejection worked
- Combine with error pages for user feedback

---

## License

MIT License
