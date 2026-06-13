# Custom provider auto-discovery in model-switcher verification

## Trigger
Use this when the user adds a provider through `hermes model` and asks whether the model-switcher/verification workflow can see it.

## Durable lesson
`hermes model` can write custom providers into `~/.hermes/config.yaml` under `custom_providers[]`, while the switcher verification script can still have a static provider list. Future verification should read `custom_providers[]` dynamically instead of requiring a hard-coded test entry for every new endpoint.

## Expected config shape
```yaml
model:
  provider: custom
  default: <model-id>
  base_url: https://example/v1
  api_key: <secret>
  compat: openai

custom_providers:
  - name: Example.Provider
    base_url: https://example/v1
    api_key: <secret>
    model: <model-id>
```

## Verification script pattern
Add a helper that reads every configured custom provider and returns test tuples:

```python
def config_custom_provider_tests() -> list[tuple[str, str, None, str]]:
    cfg = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    tests = []
    for cp in cfg.get("custom_providers", []) or []:
        name = cp.get("name") or cp.get("base_url", "custom")
        base_url = cp.get("base_url", "")
        model = cp.get("model") or cp.get("default") or ""
        if base_url and model:
            tests.append((f"custom/{name}", base_url, None, model))
    return tests
```

Then prepend it to static tests with de-duplication:

```python
seen = set()
tests = []
for item in config_custom_provider_tests() + PROVIDER_TESTS:
    if item[0] not in seen:
        tests.append(item)
        seen.add(item[0])
```

## Safety rule
Do not print or persist API keys. Redact `api_key` in all reports. The script should only read keys from config/env and send them in Authorization headers.

## Validation
Run:

```bash
python3 ~/.hermes/skills/devops/hermes-model-switcher/scripts/verify_model_switcher.py --json
```

A newly added provider should appear as `custom/<custom_providers[].name>` with its real HTTP status and token usage when successful.
