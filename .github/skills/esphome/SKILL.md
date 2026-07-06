---
name: esphome
description: >-
  ESPHome device YAML authoring and esphome.io documentation navigation.
  Use when a request touches ESPHome firmware, device configuration, components
  (sensors, binary sensors, switches, lights, GPIO, I2C, SPI, UART, BLE, OTA,
  native API, MQTT), automations, lambdas, substitutions, packages, external
  components, or HA integration of ESPHome devices. Provides a structured
  sitemap of esphome.io so the agent fetches the correct page directly instead
  of crawling, plus practical working guidance for device YAML structure.
---

# ESPHome

## When to use

- Authoring or editing ESPHome device YAML (any node under `esphome:`).
- Selecting components (sensors, binary sensors, switches, lights, climate,
  covers, displays, media players, etc.) and confirming their options.
- Wiring ESPHome devices to Home Assistant (native API vs MQTT, OTA, Bluetooth
  Proxy, Voice Assistant, micro Wake Word).
- Working with ESPHome automations, triggers, actions, conditions, lambdas,
  templates, substitutions, packages, or external components.
- Migrating from Tasmota, or starting from a ready-made project.

## When NOT to use

- Home Assistant-side integration YAML (e.g. `mqtt:` broker config, `api:` on
  the HA side, dashboard setup) — defer to the `ha-docs-sitemap` skill.
- Reading the user's actual ESPHome device files from disk — use the
  `ha-config-fetch` skill (snapshots land in `ha-data/esphome/`).
- Flashing/installing the ESPHome add-on itself — that's HA add-on management.

## Documentation research policy

- **Source of truth**: prefer the official ESPHome docs at `esphome.io` over
  blogs, forum posts, or GitHub issues. Only reference other sources when the
  official docs are insufficient, and clearly label them as non-official.
- **Knowledge freshness**: your training is out of date. ESPHome moves fast
  (component renames, new platforms, LVGL, RP2040, host platform). Do not rely
  on prior knowledge without verification — search and read the official docs
  relevant to the request first.
- **Cite exact sections**: link to the relevant doc section for any YAML or
  component option you provide. Call out version-specific behavior (e.g.
  breaking changes in the changelog) when known.
- **Fetch, don't crawl**: use [SITEMAP.md](SITEMAP.md) to find the correct
  URL, then fetch the page directly. Only follow sub-links when deeper detail
  is needed — never crawl from the root index.
- **Avoid deprecated options** and confirm syntax against docs before
  answering. Check the changelog when a component behaves unexpectedly.

## Workflow

1. Identify the topic (e.g. "LD2410 mmWave presence sensor", "OTA over HTTP",
   "BLE proxy for Home Assistant").
2. Look up the topic in [SITEMAP.md](SITEMAP.md).
3. Fetch the specific URL directly — skip the root index crawl.
4. If the topic spans multiple pages (e.g. a sensor + the `i2c` bus + the
   `sensor` core), fetch them in parallel.
5. Summarize findings and cite the exact sections used (link them).

## Working guidance

### Device YAML skeleton

A minimal ESPHome device talks to Home Assistant over the native API and
supports OTA updates. Confirm current field names against the docs before
writing — see [SITEMAP.md](SITEMAP.md) "Core / API / Network" section.

```yaml
esphome:
  name: device-name
  friendly_name: Device Name
  comment: Optional human-readable note

esp32:                       # or esp8266 / rp2040 / libretiny / host
  board: esp32dev
  framework:
    type: arduino            # or esp-idf

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:                        # fallback AP if Wi-Fi fails
    ssid: "Device-Name Fallback"

captive_portal:              # helps with onboarding when Wi-Fi fails

logger:
  level: debug

api:
  encryption:
    key: !secret api_key

ota:
  - platform: esphome
    password: !secret ota_password

web_server:
  port: 80
```

### Secrets and substitutions

- `!secret` references values from `secrets.yaml` (never committed; the fetch
  skill explicitly excludes it from snapshots).
- `substitutions:` define reusable values inline — see
  <https://esphome.io/components/substitutions/>.
- `packages:` compose reusable YAML fragments — see
  <https://esphome.io/components/packages/>.

### Home Assistant integration

- **Native API** (`api:`) is the default and recommended transport — lower
  latency than MQTT, no broker needed. HA auto-discovers the device.
- **MQTT** (`mqtt:`) is the alternative when the device is far from HA or you
  need a broker-based fanout — see <https://esphome.io/components/mqtt/>.
- **Bluetooth Proxy** forwards BLE advertisements to HA — see
  <https://esphome.io/components/bluetooth_proxy/>.
- **Voice Assistant** / **micro Wake Word** turn an ESP32 into an Assist
  endpoint — see the "Home Assistant components" section of SITEMAP.md.

### OTA and safe mode

- OTA (`ota:`) lets you push firmware updates over Wi-Fi without physical
  access. The `esphome` platform is the modern default.
- `safe_mode:` forces a known-good reboot window so a bad config can't brick
  the device — see <https://esphome.io/components/safe_mode/> and
  <https://esphome.io/components/ota/>.

### Automations and lambdas

- ESPHome automations (`on_press`, `on_value`, etc.) mirror HA automations but
  run on-device — see <https://esphome.io/automations/>.
- Lambdas embed C++ for logic YAML can't express — see
  <https://esphome.io/automations/templates/#lambda-basics>. Keep them small
  and prefer native YAML actions where possible.

## Local config snapshots

The user's actual ESPHome device YAMLs are not exposed by the HA MCP server.
Use the `ha-config-fetch` skill to refresh snapshots into `ha-data/esphome/`
(all `*.yaml` except `secrets.yaml`), then read from there. Always check the
freshness gate before reading.

## Sitemap

See [SITEMAP.md](SITEMAP.md) for the full URL reference.
