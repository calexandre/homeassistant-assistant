# Vendored files

`scripts/render.py` inlines these files into the map, so it opens from disk with no server or internet connection. They are unmodified copies from jsDelivr, and each keeps its own license header where the format allows one.

| File | Package | License | Source |
|---|---|---|---|
| `cytoscape.min.js` | cytoscape 3.30.2 | MIT | `https://cdn.jsdelivr.net/npm/cytoscape@3.30.2/dist/cytoscape.min.js` |
| `layout-base.js` | layout-base 2.0.1 | MIT | `https://cdn.jsdelivr.net/npm/layout-base@2.0.1/layout-base.js` |
| `cose-base.js` | cose-base 2.2.0 | MIT | `https://cdn.jsdelivr.net/npm/cose-base@2.2.0/cose-base.js` |
| `cytoscape-fcose.js` | cytoscape-fcose 2.2.0 | MIT | `https://cdn.jsdelivr.net/npm/cytoscape-fcose@2.2.0/cytoscape-fcose.js` |
| `roboto-latin-400-normal.woff2`, `roboto-latin-500-normal.woff2` | @fontsource/roboto 5.1.0 | Apache 2.0 | `https://cdn.jsdelivr.net/npm/@fontsource/roboto@5.1.0/files/` |

`../icons.json` holds 152 [Material Design Icons](https://pictogrammers.com/library/mdi/) from @mdi/js 7.4.47 (Apache 2.0), the icon set Home Assistant uses. `scripts/update_icons.py` regenerates it.
