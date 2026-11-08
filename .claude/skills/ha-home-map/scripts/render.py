"""Render the home map: inline the graph, icons, fonts, and libraries into one HTML file.

The output opens straight from disk, with no server and no internet connection.

Usage: render.py <graph.json> <output.html> [--title "My home"] [--offline]

Area icons missing from assets/icons.json are fetched from the jsdelivr CDN by name, unless
--offline is given; either way, an icon that cannot be found falls back to mdi:texture-box.
"""
import argparse
import base64
import datetime
import html as htmllib
import json
import pathlib
import re
import urllib.request

ASSETS = pathlib.Path(__file__).resolve().parent.parent / "assets"
VENDOR = ASSETS / "vendor"
# Load order matters: fcose needs cose-base, which needs layout-base.
SCRIPTS = ["cytoscape.min.js", "layout-base.js", "cose-base.js", "cytoscape-fcose.js"]
FONTS = [("400", "roboto-latin-400-normal.woff2"), ("500", "roboto-latin-500-normal.woff2")]
MDI_SVG = "https://cdn.jsdelivr.net/npm/@mdi/svg@7.4.47/svg/{}.svg"
FALLBACK_ICON = "mdi:texture-box"


def fetch_icon(name):
    """Fetch one MDI icon that icons.json lacks, such as an unusual area icon."""
    if not re.fullmatch(r"mdi:[a-z0-9-]+", name):
        return None
    try:
        with urllib.request.urlopen(MDI_SVG.format(name[4:]), timeout=10) as resp:
            match = re.search(rb'\sd="([^"]+)"', resp.read())
        return match.group(1).decode() if match else None
    except OSError:
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("graph")
    parser.add_argument("out")
    parser.add_argument("--title", default="Home map")
    parser.add_argument("--offline", action="store_true", help="never fetch missing icons")
    args = parser.parse_args()

    graph = json.loads(pathlib.Path(args.graph).read_text())
    icons = json.loads((ASSETS / "icons.json").read_text())
    for node in graph["nodes"]:
        name = node.get("icon")
        if name and name not in icons:
            path = None if args.offline else fetch_icon(name)
            if path:
                icons[name] = path
            else:
                print(f"icon {name} unavailable, using {FALLBACK_ICON}")
                node["icon"] = FALLBACK_ICON
    graph["icons"] = icons
    graph["meta"] = {"title": args.title, "generated": datetime.date.today().isoformat()}

    fonts = "\n".join(
        f'@font-face {{ font-family: "Roboto"; font-style: normal; font-weight: {weight}; font-display: block; '
        f'src: url(data:font/woff2;base64,{base64.b64encode((VENDOR / file).read_bytes()).decode()}) format("woff2"); }}'
        for weight, file in FONTS)
    scripts = "\n".join(f"<script>/* {name} */\n{(VENDOR / name).read_text()}\n</script>" for name in SCRIPTS)
    data = json.dumps(graph, ensure_ascii=False).replace("</", "<\\/")
    page = (ASSETS / "template.html").read_text()
    for marker, value in (("/*FONT_FACES*/", fonts), ("<!--VENDOR_SCRIPTS-->", scripts),
                          ("/*GRAPH_JSON*/null", data), ("<!--TITLE-->", htmllib.escape(args.title))):
        assert marker in page, f"{marker} missing from template.html"
        page = page.replace(marker, value)
    out = pathlib.Path(args.out)
    out.write_text(page)
    print(f"{len(page) // 1024} KB -> {out}")


if __name__ == "__main__":
    main()
