# Python 3.14 `subprocess.run` Encoding Change

Hit on Ubuntu 7.0.0-22-generic, Python 3.14.4.

## Symptom

```python
subprocess.run(["gh", "auth", "login", "--with-token"],
               input=token.encode(),  # bytes — worked in 3.12, breaks in 3.14
               capture_output=True,
               text=True)
```

## Error

```
AttributeError: 'bytes' object has no attribute 'encode'. Did you mean: 'decode'?
```

Full traceback:
```
File "/usr/lib/python3.14/subprocess.py", line 557, in run
    stdout, stderr = process.communicate(input, timeout=timeout)
File "/usr/lib/python3.14/subprocess.py", line 1221, in communicate
    stdout, stderr = self._communicate(input, endtime, timeout)
File "/usr/lib/python3.14/subprocess.py", line 2127, in _communicate
    self._save_input(input)
File "/usr/lib/python3.14/subprocess.py", line 2213, in _save_input
    self._input = self._input.encode(self.stdin.encoding, ...)
AttributeError: 'bytes' object has no attribute 'encode'. Did you mean: 'decode'?
```

## Cause

Python 3.14 changed subprocess module behavior: when `text=True` is set, the `input` parameter is expected to be a **string** and gets `.encode()` called internally. In 3.12 and earlier, bytes were accepted and auto-decoded. Passing bytes in 3.14 triggers the internal `.encode()` on an already-bytes object.

## Fix

Pass `input` as a string, not bytes:

```python
subprocess.run(["gh", "auth", "login", "--with-token"],
               input=token,  # string — works in 3.14
               capture_output=True,
               text=True)
```

## General Rule for 3.14

When using `subprocess.run()` with `text=True`:
- `input`: **string** (the pipe is text-mode)
- When `text=False` (binary mode): `input`: **bytes**
- Mixed: `text=True` + bytes `input` = crash
