#!/usr/bin/env bash
# Rebuild the demos in demo/assets/, which the showcase site publishes:
# - home-map.html: the home map of a made-up home, which the README links and the ha-home-map
#   skill hands to users without SSH snapshots, so it ships already built. The made-up home is
#   seeded, the build date is pinned, and the build skips the network (--offline).
# - release-notes.html: the release notes report rendered from demo/release-notes.json, the same
#   made-up home's report trimmed by demo/trim_release_report.py.
# Run it after any change in .claude/skills/ha-home-map/, .claude/skills/ha-release-notes/, or demo/
# and commit the result; CI fails while a committed page differs from a fresh build.
set -euo pipefail
cd "$(dirname "$0")/.."

scripts=.claude/skills/ha-home-map/scripts
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

if python3 -c 'import yaml' 2>/dev/null; then
  set -- python3 -I
elif command -v uv >/dev/null 2>&1; then
  set -- uv run --quiet --no-project --with pyyaml python3 -I
else
  echo "The graph builder needs PyYAML: pip install pyyaml, or install uv (https://docs.astral.sh/uv/)" >&2
  exit 1
fi

"$@" demo/demo_home.py "$work/home" --size medium
"$@" "$scripts/build_graph.py" --registry "$work/home/registry" --config "$work/home/config" --out "$work/graph.json" >/dev/null
SOURCE_DATE_EPOCH=1794096000 python3 -I "$scripts/render.py" "$work/graph.json" demo/assets/home-map.html --title "Demo home" --offline

python3 -I .claude/skills/ha-release-notes/scripts/release_notes.py render demo/release-notes.json \
  --html demo/assets/release-notes.html --md "$work/release-notes.md"
