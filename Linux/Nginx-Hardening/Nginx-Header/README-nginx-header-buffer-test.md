
# NGINX Header Buffer Size Test

This repository demonstrates how to test and simulate NGINX's header buffer limits using `client_header_buffer_size` and `large_client_header_buffers`.

## 📌 Goal

Simulate large HTTP headers (like `Cookie:` or `Authorization:`) and observe how NGINX responds based on configured buffer sizes.

---

## ⚙️ NGINX Configuration Example

```nginx
server {
    listen 80;
    server_name test.local;

    client_header_buffer_size 1k;
    large_client_header_buffers 2 2k;

    location /header-test {
        return 200 "✅ Header test OK";
    }
}
```

Reload NGINX:

```bash
sudo nginx -t && sudo nginx -s reload
```

> Make sure `test.local` is mapped in `/etc/hosts`:
> `127.0.0.1 test.local`

---

## 🧬 Step 1: Generate Long Header

Create a header with 5000 characters:

```bash
perl -e 'print "A"x5000' > long_header.txt
export LONG_HEADER=$(cat long_header.txt)
```

---

## 📤 Step 2: Send Curl Request

### ✅ Normal Header (Should Pass)
```bash
curl -v http://test.local/header-test   -H "X-Test-Header: short-value"
```

### ❌ Large Header (Should Fail if > buffer size)
```bash
curl -v http://test.local/header-test   -H "X-Test-Header: $LONG_HEADER"
```

### Optional: Test with Cookie
```bash
curl -v http://test.local/header-test   -H "Cookie: $LONG_HEADER"
```

---

## 🧪 Expected Behavior

| Header Size         | Behavior                     |
|----------------------|------------------------------|
| ≤ 1 KB              | ✅ 200 OK                     |
| 1–2 KB              | ✅ 200 OK via large buffer     |
| > 4 KB (2 × 2k)     | ❌ 400 Bad Request             |

---

## 🔍 Check NGINX Logs

```bash
tail -n 50 /usr/local/nginx/logs/error.log
```

Look for:

```
client sent too large header while reading client request headers
```

---

## ✅ Summary

- `client_header_buffer_size` is the default per-header limit
- `large_client_header_buffers` provides overflow protection
- Exceeding all → `400 Bad Request`
- Use `curl` + `perl` to simulate easily

---

## License

MIT License
