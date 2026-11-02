#!/usr/bin/env bash
# Publish a single parentless snapshot commit to the public repository.
#
# The inherited local history contains retired account URLs in old documentation
# commits. This script never pushes that history: it writes one commit whose tree
# is the current index and force-pushes that commit to the remote's main branch.
#
# Usage: bash scripts/publish_clean_snapshot.sh [--dry-run] [remote]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

dry_run=false
if [[ "${1:-}" == "--dry-run" ]]; then
  dry_run=true
  shift
fi
remote="${1:-origin}"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

[[ -z "$(git status --porcelain)" ]] || fail "working tree is dirty; commit or stash before publishing"

bash scripts/check_anonymity.sh
bash scripts/check_public_urls.sh

url="$(git remote get-url "$remote" 2>/dev/null || true)"
[[ -n "$url" ]] || fail "remote '$remote' is not configured"

case "$url" in
  https://github.com/*/rjbjru.git|https://github.com/*/rjbjru|git@github.com:*/rjbjru.git|git@github.com:*/rjbjru)
    ;;
  *)
    fail "remote '$remote' must point at github.com/<owner>/rjbjru, got: $url"
    ;;
esac

owner="${url#https://github.com/}"
owner="${owner#git@github.com:}"
owner="${owner%%/*}"

if [[ -f .anonymity-denylist ]]; then
  while IFS= read -r token; do
    token="${token%$'\r'}"
    [[ -z "$token" || "${token:0:1}" == "#" ]] && continue
    if grep -Fiq -- "$token" <<<"$owner"; then
      fail "remote owner contains a denylisted identifier: $owner"
    fi
  done < .anonymity-denylist
fi

tree="$(git write-tree)"
commit="$(
  GIT_AUTHOR_NAME=dev \
  GIT_AUTHOR_EMAIL=dev@users.noreply.invalid \
  GIT_COMMITTER_NAME=dev \
  GIT_COMMITTER_EMAIL=dev@users.noreply.invalid \
  git commit-tree "$tree" -m "WindLens: clean public submission snapshot"
)"

git update-ref refs/heads/public-snapshot "$commit"

if $dry_run; then
  echo "dry run: parentless commit $commit, no push performed"
  git cat-file -p "$commit"
  exit 0
fi

git push --force "$remote" "$commit:refs/heads/main"

echo
echo "published parentless snapshot $commit to $remote main"
echo "local ref: public-snapshot"
git ls-remote "$remote" refs/heads/main"
