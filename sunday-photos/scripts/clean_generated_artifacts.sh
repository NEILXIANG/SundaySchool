#!/usr/bin/env bash
set -euo pipefail

# Clean generated artifacts safely.
# - Default: remove only low-risk caches.
# - With --all: also remove build/dist/output/logs and downloaded testdata cache.
# - Never touches input/ by default (it may contain real photos).

usage() {
  cat <<'EOF'
Usage:
  bash scripts/clean_generated_artifacts.sh [--all] [--yes]

Options:
  --all   Also remove build outputs and caches: build/, dist/, output/, logs/, _downloaded_images/
  --yes   Do not prompt for confirmation

Default (no flags) removes:
  - __pycache__/ (recursive)
  - .pytest_cache/
  - .mypy_cache/
  - .pyright/

Safety:
  - Does NOT remove input/ unless you do it manually.
EOF
}

ALL=0
YES=0
for arg in "$@"; do
  case "$arg" in
    --all) ALL=1 ;;
    --yes) YES=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $arg"; usage; exit 2 ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Project: $ROOT_DIR"

delete_paths=()

# Low-risk caches
while IFS= read -r -d '' p; do delete_paths+=("$p"); done < <(find . -type d -name '__pycache__' -print0)
[[ -d .pytest_cache ]] && delete_paths+=(".pytest_cache")
[[ -d .mypy_cache ]] && delete_paths+=(".mypy_cache")
[[ -d .pyright ]] && delete_paths+=(".pyright")

if [[ "$ALL" == "1" ]]; then
  [[ -d build ]] && delete_paths+=("build")
  [[ -d dist ]] && delete_paths+=("dist")
  [[ -d output ]] && delete_paths+=("output")
  [[ -d logs ]] && delete_paths+=("logs")
  [[ -d _downloaded_images ]] && delete_paths+=("_downloaded_images")
fi

# De-dup (Bash 3.2 compatible; macOS ships bash 3.x by default)
uniq_delete_paths=()
while IFS= read -r p; do
  [[ -n "$p" ]] && uniq_delete_paths+=("$p")
done < <(printf '%s\n' "${delete_paths[@]}" | awk 'NF && !seen[$0]++')

echo "Will remove (${#uniq_delete_paths[@]}):"
for p in "${uniq_delete_paths[@]}"; do
  echo "  - $p"
done

if [[ "$YES" != "1" ]]; then
  echo
  read -r -p "Proceed? [y/N] " ans
  case "${ans,,}" in
    y|yes) ;;
    *) echo "Aborted."; exit 0 ;;
  esac
fi

for p in "${uniq_delete_paths[@]}"; do
  rm -rf "$p"
done

echo "Done."
