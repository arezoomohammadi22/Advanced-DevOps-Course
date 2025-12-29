# Tracee (Aqua Security) in Docker — Quick Test + Output Analysis

This README covers:
1) A **working docker run command** to run Tracee on the host (PID + cgroup namespaces)
2) A **simple test** that generates events (so it won’t “look stuck”)
3) How to read the **JSON output** and how to **analyze / filter** it

> Notes:
> - Tracee is an **eBPF runtime security** tool. By default it can stay quiet until events happen.
> - The commands below assume you’re on Linux with Docker and you can run `--privileged`.

---

## 1) Run Tracee (Host PID + Host Cgroup Namespace)

### Command (JSON output + only `execve` events)

```bash
docker run --rm -it   --pid=host   --cgroupns=host   --privileged   -v /sys/fs/cgroup:/sys/fs/cgroup:ro   -v /boot:/boot:ro   -v /lib/modules:/lib/modules:ro   -v /usr/src:/usr/src:ro   -v /etc/os-release:/etc/os-release-host:ro   aquasec/tracee:latest   --output json   -e execve
```

### What each flag means (short)
- `--pid=host` : Tracee sees **host processes** (not only container processes).
- `--cgroupns=host` : Tracee sees **host cgroups**, better container visibility/metadata.
- `--privileged` : required for most eBPF use cases in a container.
- `-v /lib/modules:/lib/modules:ro` : gives access to kernel modules info (often required).
- `-v /usr/src:/usr/src:ro` : kernel headers may be used depending on kernel setup.
- `-v /boot:/boot:ro` : allows reading `/boot/config-$(uname -r)` to detect kconfig features.
- `-v /sys/fs/cgroup:/sys/fs/cgroup:ro` : access to host cgroup FS (enrichment).
- `--output json` : prints events as JSON (easy to parse).
- `-e execve` : only show process execution events (good for testing).

---

## 2) “It’s stuck” vs “It’s waiting” — Generate Events

**Tracee is event-driven**. If nothing happens, it may print nothing.

### In another terminal, run a few commands on the host
```bash
ls
whoami
uname -a
```

You should start seeing `execve` events.

### Also generate container events (recommended test)
```bash
docker run --rm alpine sh -c "id; uname -a; echo hello >/tmp/x; ps"
```

If Tracee is running correctly, you’ll see events for processes executed inside that container too.

---

## 3) What the JSON Output Means

When Tracee prints an event, you’ll get a JSON object (one per line).  
Typical `execve` event fields you may see (field names can vary slightly by version):

### Common fields
- `eventName` or `event_name`  
  **Which event** it is (here it should be `execve`).
- `timestamp` / `ts`  
  Event time.
- `hostName`  
  Hostname of the machine.
- `processName` / `comm`  
  The binary name (e.g., `bash`, `sh`, `curl`, `apt`, `docker`).
- `pid` / `processId`  
  PID of the process on the host PID namespace (because `--pid=host`).
- `ppid`  
  Parent PID (helps build a process tree).
- `uid` / `gid` and/or `userId`  
  Which user executed the process.
- `args` / `argv`  
  The executed command arguments (the **most useful** part for hunting).
- `cwd`  
  Current working directory at execution time (helpful context).
- `container` / `containerId` / `containerName`  
  If Tracee can map the process to a container.
- `cgroupId` / `cgroup`  
  Used to associate events with containers / pods (enrichment).

### Example (illustrative)
```json
{
  "eventName": "execve",
  "timestamp": 1767019999,
  "processName": "sh",
  "pid": 12345,
  "ppid": 12000,
  "uid": 0,
  "args": ["sh","-c","id; uname -a; echo hello >/tmp/x"],
  "containerId": "e8c7...abcd",
  "containerName": "alpine"
}
```

How to read this:
- A process named `sh` executed (event `execve`)
- It ran as `uid: 0` (root)
- It executed the command shown in `args`
- Tracee mapped it to a container (container id/name)

---

## 4) How to Analyze the Output (Practical)

### A) Look for suspicious exec patterns
Focus on `args` / `argv`. Examples of suspicious commands:
- reverse shells (`bash -i`, `/dev/tcp/`, `nc -e`)
- download & execute (`curl ... | sh`, `wget ... | sh`)
- crypto miners (`xmrig`, `minerd`)
- unexpected package installs on prod (`apt install`, `yum install`)
- privilege escalation tools (`sudo`, `su`, `pkexec`)

### B) Track parent/child relationships
Use `pid` + `ppid` to reconstruct the chain:
- Who launched what?
- From which shell / service?

Example interpretation:
- `systemd` → `bash` → `curl` → `sh`  
This chain is often more meaningful than single commands.

### C) Separate host vs container activity
If the event has `containerId/containerName`, it likely came from a container.
If there is no container info, it may be host activity or container enrichment failed.

---

## 5) Save Output to a File and Filter It

### Save JSON lines to a file
```bash
docker run --rm -i   --pid=host   --cgroupns=host   --privileged   -v /sys/fs/cgroup:/sys/fs/cgroup:ro   -v /boot:/boot:ro   -v /lib/modules:/lib/modules:ro   -v /usr/src:/usr/src:ro   -v /etc/os-release:/etc/os-release-host:ro   aquasec/tracee:latest   --output json   -e execve | tee tracee-execve.jsonl
```

### Quick filtering with `jq` (recommended)
Install jq if needed:
```bash
sudo apt update && sudo apt install -y jq
```

Filter only events from containers:
```bash
jq -c 'select(.containerId != null or .container != null)' tracee-execve.jsonl
```

Print only command args:
```bash
jq -r '.args // .argv // empty | join(" ")' tracee-execve.jsonl
```

Show process name + pid + args:
```bash
jq -r '[.processName // .comm, (.pid|tostring), (.args // .argv // []) | join(" ")] | @tsv' tracee-execve.jsonl
```

Search for suspicious patterns (examples):
```bash
grep -Ei '(/dev/tcp|nc -e|curl .*\| *sh|wget .*\| *sh|xmrig|minerd)' tracee-execve.jsonl
```

---

## 6) Troubleshooting

### “No output / looks stuck”
- It’s often just **waiting for events**.
- Run commands on host or start a container workload (Section 2).

### Warnings about `/boot/config-*` missing
Mount `/boot` (already included above).  
If your host truly doesn’t have `/boot/config-$(uname -r)`, Tracee may “assume” kconfig values.

### Cgroup warning
Use `--cgroupns=host` + mount `/sys/fs/cgroup` (already included).

---
