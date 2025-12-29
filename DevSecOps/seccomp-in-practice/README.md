# Seccomp Testing Guide (Modern Linux / Docker)

This README documents **end‑to‑end testing of seccomp profiles** in Docker, including **modern Linux mount behavior**, common pitfalls, and **correct verification techniques**.

The content is based on real hands‑on debugging and shows **why simple seccomp rules sometimes appear to not work**, and how to fix and prove them.

---

## 1. What We Are Testing

Goal:
- Prove that **seccomp is actually applied**
- Demonstrate **blocking a syscall** (mount)
- Understand **why mount may still succeed** on modern kernels
- Learn how to **correctly test seccomp behavior**

Key idea:
> seccomp filters **syscalls**, not commands.

---

## 2. Environment

- Host: Linux (modern kernel)
- Runtime: Docker
- Image: `registry.sananetco.com/devops/nginx`
- Shell: `/bin/bash`

---

## 3. Initial Seccomp Profile (Naive – Legacy)

```json
{
  "defaultAction": "SCMP_ACT_ALLOW",
  "syscalls": [
    {
      "names": ["mount"],
      "action": "SCMP_ACT_ERRNO",
      "errnoRet": 1
    }
  ]
}
```

Expectation:
- `mount` should fail

Reality:
- On modern Linux, **mount still succeeds**

---

## 4. Why Blocking `mount` Did NOT Work

Modern versions of `mount` (util‑linux) **do NOT call the legacy `mount()` syscall**.

Instead, they use the **new Linux Mount API**.

Confirmed via `strace`:

```bash
strace -f -e trace=mount,umount2,open_tree,move_mount,fsopen,fsconfig,fsmount,mount_setattr \
  mount -t tmpfs tmpfs /mnt
```

Observed syscalls:

```text
fsopen("tmpfs")
fsconfig(...)
fsmount(...)
move_mount(...)
```

Conclusion:
> The syscall `mount()` was never invoked, so seccomp rules for it never matched.

---

## 5. Correct Understanding of Seccomp Order

Execution flow:

1. User executes `/bin/mount`
2. Capability checks happen first (e.g. `CAP_SYS_ADMIN`)
3. Syscall is invoked
4. **seccomp filter is evaluated**
5. Kernel allows / denies

Important:
- If capability check fails → syscall never reaches seccomp
- seccomp is evaluated **after capability checks**

---

## 6. Proper Test Setup (Required)

To test seccomp correctly for `mount`, capability checks must NOT block the syscall.

Therefore:

```bash
docker run --rm -it \
  --cap-add SYS_ADMIN \
  --security-opt seccomp=./seccomp-profile.json \
  registry.sananetco.com/devops/nginx /bin/bash
```

This ensures:
- `mount` syscall path is reachable
- seccomp is the deciding factor

---

## 7. Correct Seccomp Profile for Modern Mount API

### Minimal (recommended – clean failure)

```json
{
  "defaultAction": "SCMP_ACT_ALLOW",
  "syscalls": [
    { "names": ["move_mount"], "action": "SCMP_ACT_ERRNO", "errnoRet": 1 }
  ]
}
```

Result:
- mount setup occurs
- attach step fails
- mount does NOT appear

---

### Full (covers all modern mount syscalls)

```json
{
  "defaultAction": "SCMP_ACT_ALLOW",
  "syscalls": [
    { "names": ["mount"],       "action": "SCMP_ACT_ERRNO", "errnoRet": 1 },
    { "names": ["fsopen"],      "action": "SCMP_ACT_ERRNO", "errnoRet": 1 },
    { "names": ["fsconfig"],    "action": "SCMP_ACT_ERRNO", "errnoRet": 1 },
    { "names": ["fsmount"],     "action": "SCMP_ACT_ERRNO", "errnoRet": 1 },
    { "names": ["move_mount"],  "action": "SCMP_ACT_ERRNO", "errnoRet": 1 },
    { "names": ["open_tree"],   "action": "SCMP_ACT_ERRNO", "errnoRet": 1 },
    { "names": ["mount_setattr"], "action": "SCMP_ACT_ERRNO", "errnoRet": 1 }
  ]
}
```

---

## 8. Testing the Result

Inside the container:

```bash
mount -t tmpfs tmpfs /mnt
echo $?
df -h | grep " /mnt$"
```

Expected:
- Exit code != 0
- `/mnt` is NOT mounted

---

## 9. Kill vs Error Behavior

### ERRNO (recommended for learning)

```json
"action": "SCMP_ACT_ERRNO"
```

- Command fails gracefully
- Error visible

---

### KILL_PROCESS (hard enforcement)

```json
"action": "SCMP_ACT_KILL_PROCESS"
```

Behavior:
- The syscall‑issuing process is terminated
- Shell may survive
- No error message is guaranteed

---

## 10. How to Prove Seccomp Is the Cause

### Method 1: `strace`

```bash
strace -f -e trace=move_mount mount -t tmpfs tmpfs /mnt
```

Failure here confirms seccomp enforcement.

---

### Method 2: Kernel Logs (Host)

```bash
dmesg | tail -n 50
```

Look for:
- `seccomp`
- `audit`
- `denied syscall`

---

## 11. Key Lessons (Very Important)

- seccomp filters **syscalls**, not binaries
- Modern Linux uses **new mount API**, not `mount()`
- Capability checks run **before** seccomp
- Blocking legacy syscalls alone is insufficient
- `strace` is mandatory for writing correct seccomp profiles

---

## 12. Recommended Production Strategy

- Keep Docker default seccomp enabled
- Add **custom deny rules only when necessary**
- Prefer `ERRNO` for debugging, `KILL_PROCESS` for enforcement
- Always verify behavior using `strace`

---

## 13. Summary

This guide demonstrates:
- Why seccomp may appear "not applied"
- How modern kernels change syscall behavior
- How to correctly test and validate seccomp enforcement

If seccomp is tested incorrectly, it gives false confidence.
If tested correctly, it is one of the strongest kernel‑level defenses available.

---

End of README

