#!/usr/bin/env bash
# Generate an anonymous, lower-case repository name. The human still decides
# whether the owning GitHub account is anonymous (H2).
set -euo pipefail

python3 - <<'PY'
import secrets
import string

alphabet = string.ascii_lowercase
print("windlens-" + "".join(secrets.choice(alphabet) for _ in range(6)))
PY
