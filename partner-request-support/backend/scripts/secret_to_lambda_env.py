#!/usr/bin/env python3
"""
Convert AWS Secrets Manager SecretString into Lambda update-function-configuration JSON.

Supports:
  - {"Variables": {"KEY": "value", ...}}  -> pass through (values coerced to str)
  - {"KEY": "value", ...} flat JSON       -> wrap as Variables
  - .env lines (KEY=value, # comments)     -> build Variables

Usage: python3 secret_to_lambda_env.py <input_path> <output_path>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def stringify_vars(d: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in d.items():
        if not isinstance(k, str) or not k.strip():
            continue
        if v is None:
            out[k] = ""
        elif isinstance(v, (dict, list)):
            out[k] = json.dumps(v, ensure_ascii=False)
        else:
            out[k] = str(v)
    return out


def parse_env_file(content: str) -> dict[str, str]:
    """Parse KEY=value .env style (multiline values not supported)."""
    variables: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip optional surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if key:
            variables[key] = value
    return variables


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: secret_to_lambda_env.py <input_path> <output_path>", file=sys.stderr)
        return 2

    inp = Path(sys.argv[1])
    outp = Path(sys.argv[2])
    raw = inp.read_text(encoding="utf-8-sig").strip()
    if not raw:
        print("Empty secret file", file=sys.stderr)
        return 1

    # Try JSON
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            if "Variables" in data and isinstance(data["Variables"], dict):
                payload = {"Variables": stringify_vars(data["Variables"])}
            else:
                payload = {"Variables": stringify_vars(data)}
            outp.write_text(json.dumps(payload), encoding="utf-8")
            return 0
    except json.JSONDecodeError:
        pass

    # .env style
    variables = parse_env_file(raw)
    if not variables:
        print(
            "Could not parse secret as JSON or .env (no KEY=value pairs found)",
            file=sys.stderr,
        )
        return 1

    outp.write_text(json.dumps({"Variables": variables}), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
