# .env Key Leading Space Bug (2026-06-13)

## Symptoms

- API returns HTTP 401 "Incorrect API key" even though key char set, length, prefix all correct
- sha256 of key from `.env` differs from sha256 of the "clean" version
- `hexdump -C .env | grep KEY` shows `3d 20 73 6b` (0x20 = space between `=` and `sk-`)

## Root Cause

`.env` line format: `DEEPSEEK_API_KEY=*** — the `=` sign is followed by a space before the key.

When parsed with `line.split("=", 1)[1].rstrip()`:
- `rstrip()` only removes trailing whitespace (newline)
- The **leading space after `=` is preserved**
- Result: key becomes ` sk-602...` (35 chars + 1 leading space = 36 chars)

DeepSeek API sees the leading space and returns 401.

## Detection

```bash
# Hex dump shows 0x20 (space) after KEY=
hexdump -C ~/.hermes/.env | grep DEEPSEEK | head -2
# Look for: 5f 4b 45 59 3d 20 73 6b → "_KEY= sk"

# Python check
python3 -c "
with open('/root/.hermes/.env', 'rb') as f:
    for line in f:
        if b'DEEPSEEK_API_KEY' in line and b'BASE' not in line:
            val = line.split(b'=', 1)[1]
            print(f'val: {val!r}')
            print(f'len: {len(val)}')
            print(f'starts with space: {val.startswith(b\" \")}')
"
```

## Fix

**Option A: Clean `.env` file** (recommended):
```python
with open('/root/.hermes/.env', 'rb') as f:
    raw = f.read()
# Replace "= " with "=" only at the start of key lines
clean = raw.replace(b'KEY= ', b'KEY=')  # adjust per key name
with open('/root/.hermes/.env', 'wb') as f:
    f.write(clean)
```

**Option B: Tool-level compatibility** (defensive):
```python
# In read function: use .strip() not .rstrip()
key = line.split("=", 1)[1].strip()  # removes leading AND trailing whitespace
# NOT: key = line.split("=", 1)[1].rstrip()  # only trailing
```

## Prevention

When writing `.env` keys:
- Use `echo -n "key" >> .env` (no newline)
- Or Python `f.write(f'KEY={key}\n')` (no space between `=` and key)
- Never manually type `KEY= key` with space after equals

## Lessons for Tool Development

Any `.env` parser should use `.strip()` not `.rstrip()`. This bug affected:
- `hermes-switcher` set_model() → api_key sync
- OpenAI SDK init → 401 on all providers
- DeepSeek API → 401
- minimax API → 401 (same root cause)

**Pattern**: `line.split("=", 1)[1].strip()` is the universal safe read pattern.