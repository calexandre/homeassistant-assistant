"""Regenerate assets/icons.json: the Material Design Icons the home map can draw offline.

Home Assistant names icons `mdi:<name>`. This script reads @mdi/js and keeps only the
icons below: every device-type, node, and UI icon the map uses, plus common area icons.
render.py fetches any other area icon at build time and falls back to mdi:texture-box.

Usage: update_icons.py <path to @mdi/js mdi.js>
Get the file from https://cdn.jsdelivr.net/npm/@mdi/js@7.4.47/mdi.js (Apache 2.0).
"""
import json
import pathlib
import re
import sys

NAMES = """
access-point-network air-conditioner arrow-right bluetooth check chevron-down close cloud-outline
content-copy devices download eye-off-outline filter-variant fit-to-screen-outline flash floor-plan
graph-outline help-circle-outline home-outline information-outline magnify menu minus palette plus
restore robot script-text table texture-box theme-light-dark wifi z-wave zigbee
blinds cctv cellphone coffee-maker dishwasher door-open fan flower fridge hub light-switch lightbulb
lock motion-sensor play-box power-plug printer radiator remote robot-vacuum router-wireless speaker
stove television thermometer water-alert water-boiler washing-machine
archive baby-face baby-face-outline balcony bathtub bathtub-outline bed bed-double bed-empty bed-king
bed-king-outline book-open-variant bookshelf broom car car-outline cat ceiling-light chair-rolling
coffee controller countertop desk desk-lamp dog door door-closed dumbbell faucet faucet-variant
fireplace flower-outline food food-fork-drink fridge-outline gamepad-variant garage garage-variant
glass-wine grass grill guitar-acoustic hammer-wrench hanger home home-floor-0 home-floor-1
home-floor-2 home-roof human-child iron laptop lightbulb-outline monitor movie-open music
office-building package-variant paper-roll paw piano pine-tree pool router-network server
server-network shower shower-head silverware-fork-knife sofa sofa-outline sprout stairs stairs-down
stairs-up table-chair table-furniture television-classic theater toilet tools tree tshirt-crew
tumble-dryer umbrella-beach wardrobe wardrobe-outline weather-sunny window-open-variant yoga
""".split()


def camel(name):
    return "mdi" + "".join(part.capitalize() for part in name.split("-"))


source = pathlib.Path(sys.argv[1]).read_text()
paths = dict(re.findall(r'^export var (mdi\w+) = "([^"]+)";', source, re.M))
icons, missing = {}, []
for name in sorted(set(NAMES)):
    path = paths.get(camel(name))
    if path:
        icons[f"mdi:{name}"] = path
    else:
        missing.append(name)
out = pathlib.Path(__file__).resolve().parent.parent / "assets" / "icons.json"
out.write_text(json.dumps(icons, indent=0, sort_keys=True) + "\n")
print(f"{len(icons)} icons -> {out}")
if missing:
    print("not in @mdi/js:", ", ".join(missing))
