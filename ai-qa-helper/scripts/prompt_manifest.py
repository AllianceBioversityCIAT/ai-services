"""Checks (default) or completes prompts/manifest.json.

    uv run python -m scripts.prompt_manifest           # verify every pinned sha256
    uv run python -m scripts.prompt_manifest --fill    # set sha256 only where it is empty

``--fill`` never overwrites a pinned hash: a released promptVersion must not change. To change a
prompt, add a new version with new files and run ``--fill``.
"""

import json
import sys

from app.prompts.loader import PROMPTS_DIR, file_sha256


def _entries(manifest: dict):
    for version in manifest["versions"].values():
        if "system" in version:
            yield version["system"]
        yield from version["fields"].values()
    yield from manifest.get("inactive", {}).values()


def main(argv: list[str]) -> int:
    path = PROMPTS_DIR / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    fill = "--fill" in argv
    bad = []
    for entry in _entries(manifest):
        actual = file_sha256(PROMPTS_DIR / entry["file"])
        if not entry["sha256"] and fill:
            entry["sha256"] = actual
        elif entry["sha256"] != actual:
            bad.append(entry["file"])
    if fill:
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for f in bad:
        print(f"sha256 mismatch: {f}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
