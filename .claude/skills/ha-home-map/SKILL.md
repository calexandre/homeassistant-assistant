---
name: ha-home-map
description: >-
  Draws an offline, interactive map of the home: every area as a card, its
  devices, and the automations, scripts, and scenes that trigger or control
  them, saved to .temp/home-map/home-map.html.
disable-model-invocation: true
---

# HA Home Map

Builds one HTML file from the Home Assistant registries and YAML: areas as cards, devices colored by connection type, and the automations, scripts, and scenes that link them. It opens straight from disk with no server or internet connection, and it describes the user's home, so it stays on this machine.

`<skill>` below is this skill's folder: `.claude/skills/ha-home-map` in a clone of this repository, or the base directory shown when the skill loads from an installed plugin. The fetch script lives beside it, in `<skill>/../ha-config-fetch/`, and the prebuilt demo three folders up, in `<skill>/../../../demo/assets/home-map.html`.

## Input

An optional page title, such as `/ha-home-map Beach house`. Default: `Home map`.

## Step 1 — Fresh snapshot

The map reads `ha-data/configuration.yaml` with the files it includes, and the trimmed registries in `ha-data/registry/`. Check both in one go:

```bash
[ -s ha-data/registry/entries.json ] && [ -z "$(find ha-data/configuration.yaml ha-data/registry/entries.json -mmin +1440)" ] && echo FRESH || echo STALE
```

- FRESH: go to Step 2.
- STALE: run `<skill>/../ha-config-fetch/fetch-ha-data.sh` from the project root.
- The fetch exits with `Cannot reach 'homeassistant' over passwordless SSH`: tell the user the map needs SSH snapshots and point them at the README's "Optional: SSH snapshots" section. Offer the prebuilt demo of a made-up home instead (Step 2, demo branch).

Done when `ha-data/registry/` holds `areas.json`, `devices.json`, `entities.json`, and `entries.json`, all under a day old.

## Step 2 — Build the map

The graph builder needs PyYAML. Use plain `python3` when it has it, and `uv` to supply it otherwise:

```bash
if python3 -c 'import yaml' 2>/dev/null; then set -- python3 -I; else set -- uv run --quiet --no-project --with pyyaml python3 -I; fi
mkdir -p .temp/home-map
"$@" <skill>/scripts/build_graph.py --registry ha-data/registry --config ha-data --out .temp/home-map/graph.json \
  && python3 -I <skill>/scripts/render.py .temp/home-map/graph.json .temp/home-map/home-map.html --title "Home map"
```

When neither PyYAML nor `uv` is installed, tell the user to install one (`pip install pyyaml`, or `uv` from <https://docs.astral.sh/uv/>) and stop.

`render.py` fetches an area icon that `assets/icons.json` lacks from the jsdelivr CDN by its name (such as `mdi:sofa`); add `--offline` when the user wants no network request, and such icons fall back to a plain one.

Demo branch, for a user without SSH snapshots: the demo ships already built, so copy it into the output folder; it needs no PyYAML and no build:

```bash
mkdir -p .temp/home-map/demo && cp <skill>/../../../demo/assets/home-map.html .temp/home-map/demo/home-map.html
```

When the copy fails because the install has no `demo/` folder, link the demo on GitHub instead: <https://github.com/calexandre/homeassistant-assistant/blob/main/demo/assets/home-map.html>, which the user downloads and opens.

Done when `render.py` prints the size and path of the HTML file, or, in the demo branch, when the copy exists.

## Step 3 — Reply

`build_graph.py` prints the map's stats as JSON. Reply with:

1. The file as a Markdown link relative to the working directory, such as `[.temp/home-map/home-map.html](.temp/home-map/home-map.html)`. When `WSL_DISTRO_NAME` is set, add the address that opens it in a Windows browser: `file://wsl.localhost/<distro><absolute path>`.
2. One line of counts: areas, devices, automations, scripts, and scenes on the map.
3. The automations in `not_on_map`, which touch no device or area (notifications, template-only logic): name up to ten and count the rest.
4. When `unresolved_refs_by_domain` is not empty, one line naming its domains: entity references that belong to no device, such as helpers, people, and template sensors, so they draw no line.

For the demo, reply with item 1 only, and say the map shows a made-up home, not theirs.

For follow-up questions such as "what turns on the hallway light?", read `.temp/home-map/graph.json`: `nodes` hold areas, devices, automations, scripts, and scenes with their `parent` area, and `edges` link them by `kind` (`trigger`, `control`, or `call`).

## Rules

- Write every output under `.temp/home-map/`, which git ignores; leave it uncommitted.
- Share the map only by its local path. Publish or upload it only when the user asks, since it lists their rooms, devices, and routines.
