"""Personalized Home Assistant release notes: parse the release posts, match them to the home,
merge the agent's judgments, and render the report as HTML and Markdown.

  release_notes.py build  (--ha-data DIR | --domains a,b,c) [--target VERSION|URL] [--from VERSION]
                          [--out-dir ha-release-notes] [--todo FILE] [--source-dir DIR]
  release_notes.py assess REPORT.json < judgments.json
  release_notes.py render REPORT.json [--html FILE] [--md FILE]

build   finds every release from the installed version (--from, or ha-data/.HA_VERSION) up to the
        target (default: the newest release), parses each post's Markdown source from the
        home-assistant.io repo, matches the items to the home, and writes REPORT.json with empty
        judgments plus a to-do list for the agent. Prints UP TO DATE and writes nothing when the
        installed version already is the target or newer.
assess  merges the agent's judgments (JSON on stdin, keyed by item id) into REPORT.json, then
        renders the HTML and Markdown once every required judgment is there.
render  renders REPORT.json again, for example after editing it by hand.
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import post_parser  # noqa: E402
import report as report_render  # noqa: E402

ATOM = "https://www.home-assistant.io/blog/categories/release-notes/atom.xml"
RAW = "https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source"
SITE = "https://www.home-assistant.io"
POST_LINK = re.compile(r"/blog/(\d{4})/(\d{2})/(\d{2})/release-(\d{4})(\d{1,2})/")
VERSION = re.compile(r"^(\d{4})\.(\d{1,2})(?:\.(\d+))?([a-z][a-z0-9]*)?$")
MAX_MONTHS = 24
AFFECTS = ("action", "behavior", "opportunity", "none")
TEXT_LIMIT = {"highlight": 1500, "default": 3000}


def fail(message, code=1):
    print(message, file=sys.stderr)
    sys.exit(code)


# --- versions ------------------------------------------------------------------------------------
def parse_version(text):
    """(year, month, patch); patch is None when not given and -1 for a beta or dev build of .0."""
    match = VERSION.match(str(text).strip())
    if not match or not 1 <= int(match.group(2)) <= 12:
        fail(f"Not a Home Assistant version: {text!r}. Use one like 2026.11 or 2026.11.1.", 2)
    patch = int(match.group(3)) if match.group(3) is not None else None
    if match.group(4):
        patch = -1 if not patch else patch - 1  # 2026.11.0b3 comes before 2026.11.0
    return int(match.group(1)), int(match.group(2)), patch


def version_text(version):
    year, month, patch = version
    return f"{year}.{month}.{max(patch or 0, 0)}"


def month_key(release):
    parts = [int(p) for p in release.split(".")]
    return parts[0], parts[1], parts[2] if len(parts) > 2 else 0


def next_month(year, month):
    return (year + 1, 1) if month == 12 else (year, month + 1)


# --- sources -------------------------------------------------------------------------------------
class Source:
    """Fetches the release posts, or reads them from a folder (tests, offline runs) by file name."""

    def __init__(self, folder=None):
        self.folder = pathlib.Path(folder) if folder else None

    def get(self, url):
        if self.folder:
            path = self.folder / url.rstrip("/").rsplit("/", 1)[-1]
            if not path.is_file():
                fail(f"Not in {self.folder}: {path.name} (for {url})")
            return path.read_text(encoding="utf-8")
        request = urllib.request.Request(url, headers={"User-Agent": "homeassistant-assistant-release-notes"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as err:
            fail(f"Could not fetch {url}: {err}")

    def latest_month(self):
        match = POST_LINK.search(self.get(ATOM))
        if not match:
            fail(f"No release post found in {ATOM}")
        return int(match.group(4)), int(match.group(5))

    def post(self, year, month):
        """The parsed post for a monthly release, found through its changelog's link to the blog."""
        changelog = self.get(f"{RAW}/changelogs/core-{year}.{month}.markdown")
        link = next((m for m in POST_LINK.finditer(changelog)
                     if (int(m.group(4)), int(m.group(5))) == (year, month)), None)
        if not link:
            fail(f"The {year}.{month} changelog links no release post")
        y, mm, dd = link.group(1), link.group(2), link.group(3)
        markdown = self.get(f"{RAW}/_posts/{y}-{mm}-{dd}-release-{year}{month}.markdown")
        url = f"{SITE}/blog/{y}/{mm}/{dd}/release-{year}{month}/"
        return post_parser.parse_post(markdown, f"{year}.{month}", url)


# --- build ---------------------------------------------------------------------------------------
def build_date():
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        return datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc).date().isoformat()
    return datetime.date.today().isoformat()


def resolve_target(source, target):
    if not target:
        year, month = source.latest_month()
        return year, month, None
    url = re.search(r"release-(\d{4})(\d{1,2})/?(?:#.*)?$", target)
    if target.startswith("http"):
        if not url:
            fail(f"Not a Home Assistant release post URL: {target}", 2)
        return int(url.group(1)), int(url.group(2)), None
    return parse_version(target)


def installed_version(args):
    if args.from_version:
        return parse_version(args.from_version), "argument"
    marker = pathlib.Path(args.ha_data or "", ".HA_VERSION")
    if args.ha_data and marker.is_file():
        text = marker.read_text().strip()
        if VERSION.match(text):
            return parse_version(text), "snapshot"
    return None, None


def build(args):
    if not args.ha_data and args.domains is None:
        fail("Pass --ha-data DIR (SSH snapshots) or --domains a,b,c (from GetLiveContext).", 2)
    import inventory
    if args.ha_data:
        if not (pathlib.Path(args.ha_data) / "registry" / "entries.json").is_file():
            fail(f"No registries in {args.ha_data}/registry: refresh the snapshot, or pass --domains instead.", 2)
        home = inventory.from_snapshot(args.ha_data)
    else:
        home = inventory.from_domains(args.domains.split(","))

    source = Source(args.source_dir)
    ty, tm, tp = resolve_target(source, args.target)
    posts = {(ty, tm): source.post(ty, tm)}
    if tp is None:
        tp = max([month_key(v)[2] for v in posts[(ty, tm)]["patches"]], default=0)
    target = (ty, tm, tp)

    installed, installed_from = installed_version(args)
    if installed and installed[2] is None:
        installed = (installed[0], installed[1], 0)
    if installed and installed >= target:
        print(f"UP TO DATE: installed {version_text(installed)} is already at or past {version_text(target)}.")
        return

    months = [(ty, tm)]
    if installed:
        months, ym = [], installed[:2]
        while ym <= (ty, tm):
            months.append(ym)
            ym = next_month(*ym)
        if len(months) > MAX_MONTHS:
            fail(f"{version_text(installed)} to {version_text(target)} spans {len(months)} releases; "
                 f"pass --from with a version at most {MAX_MONTHS} releases back.", 2)
    for ym in months:
        if ym not in posts:
            posts[ym] = source.post(*ym)

    items, notes = [], []
    for ym in months:
        post = posts[ym]
        notes += post["warnings"]
        for item in post["items"]:
            if item["kind"] == "patch":
                version = month_key(item["release"])
                keep = version <= target and (not installed or version > installed)
            else:
                keep = not installed or ym > installed[:2] or installed[2] < 0
            if keep:
                items.append(item)

    for item in items:
        used = [d for d in item["domains"] if d in home["domains"]]
        item["match"] = None
        if used and item["kind"] != "patch":
            used_by = sorted({eid for d in used for eid in home["domains"][d]["used_by"]})
            item["match"] = {"domains": used, "used_by": used_by}
        item["general"] = item["kind"] == "breaking" and not item["domains"]
        item["assessment"] = None
        if args.no_text:
            item.pop("text", None)

    if home["source"] == "live_context":
        notes.insert(0, "Matched without SSH snapshots, from the entity domains GetLiveContext shows: "
                        "integrations and YAML-only setups may be missed.")
    if not installed:
        notes.insert(0, f"The installed version is unknown, so this covers only {ty}.{tm}. "
                        "Pass a from version to include the releases you would skip.")

    report = {
        "schema": 1,
        "meta": {"target": version_text(target), "installed": version_text(installed) if installed else None,
                 "installed_from": installed_from, "generated": build_date(), "inventory": home["source"],
                 "author": None, "model": None, "summary": None, "notes": notes},
        "posts": [{k: posts[ym][k] for k in ("release", "title", "url", "date")} for ym in months],
        "inventory": home,
        "items": items,
        "verdict": None,
    }
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"ha-release-{report['meta']['target']}.json"
    save(path, report)
    todo = pathlib.Path(args.todo or f".temp/release-notes/todo-{report['meta']['target']}.md")
    todo.parent.mkdir(parents=True, exist_ok=True)
    todo.write_text(to_do(report, path), encoding="utf-8")

    counts = {}
    for item in items:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1
    print(f"Report: {path}")
    print(f"To-do: {todo}")
    print(f"Span: {report['meta']['installed'] or 'unknown'} -> {report['meta']['target']} "
          f"({', '.join(p['release'] for p in report['posts'])})")
    print(f"Items: {json.dumps(counts)}; matched to this home: {sum(1 for i in items if i['match'])}; "
          f"required judgments: {len(missing(report)) - 2} plus the verdict and summary")
    for note in notes:
        print(f"Note: {note}")


def save(path, report):
    pathlib.Path(path).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def clip(text, limit):
    text = text or ""
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " […]"


def to_do(report, path):
    meta, home = report["meta"], report["inventory"]
    items = report["items"]
    logic = home.get("logic") or {}
    lines = [f"# Release notes to-do: {meta['installed'] or '?'} -> {meta['target']}", "",
             f"Report: {path}", f"Releases: {', '.join(p['release'] for p in report['posts'])}",
             f"Matched from: {'registries and YAML (SSH snapshots)' if home['source'] == 'registries' else 'GetLiveContext entity domains'}"]
    used = [f"{d} ({v['entries']} entries, {v['entities']} entities{', YAML' if v['yaml'] else ''})"
            for d, v in home["domains"].items() if v["entries"] or v["yaml"] or v["entities"]]
    lines += [f"Domains in use: {', '.join(used) if used else ', '.join(home['domains'])}", ""]
    for note in meta["notes"]:
        lines.append(f"Note: {note}")

    def block(title, picked, full=True, limit=None):
        if not picked:
            return
        lines.extend(["", f"## {title}", ""])
        for item in picked:
            label = report_render.KIND_LABEL[item["kind"]]
            head = f"[{item['id']}] {item['title']} ({label}, {item['release']})"
            if not full:
                extra = f" — domains: {', '.join(item['domains'])}" if item["domains"] else ""
                description = (item.get("text") or "").split("\n", 1)[-1]  # below the "Name, added by" line
                first = clip(description.replace("\n", " "), 200) if item["kind"] == "new_integration" else ""
                lines.append(f"- {head}{extra}{': ' + first if first else ''}")
                continue
            lines.append(f"### {head}")
            if item["domains"]:
                lines.append(f"Domains: {', '.join(item['domains'])}")
            if item.get("match") and item["match"]["used_by"]:
                names = [f"{logic.get(e, e)} ({e})" for e in item["match"]["used_by"][:12]]
                more = len(item["match"]["used_by"]) - 12
                lines.append(f"Used by: {', '.join(names)}{f' and {more} more' if more > 0 else ''}")
            lines.extend([clip(item.get("text"), limit or TEXT_LIMIT["default"]), ""])

    highlights = [i for i in items if i["kind"] == "highlight"]
    matched = [i for i in items if i["match"] and i["kind"] != "highlight"]
    general = [i for i in items if i["general"]]
    block("1. Highlights: required, a summary for each; add impact and affects when it touches this home",
          highlights, limit=TEXT_LIMIT["highlight"])
    block("2. Matched to this home: required, affects for each", matched)
    block("3. Breaking changes naming no integration: required, affects for each (search ha-data/ for the feature)",
          general)
    block("4. Removed integrations: optional, judge any this home uses", [i for i in items if i["kind"] == "removed" and not i["match"]], full=False)
    block("5. New integrations: optional, mark the ones that fit this home as opportunity",
          [i for i in items if i["kind"] == "new_integration" and not i["match"]], full=False)
    block("6. Patch fixes: optional, judge the ones that touch this home's integrations",
          [i for i in items if i["kind"] == "patch"], full=False)
    block("7. Other changes not matched: optional", [i for i in items if i["kind"] in ("improvement", "now_in_ui", "noteworthy")
                                                    and not i["match"]], full=False)
    return "\n".join(lines).rstrip() + "\n"


# --- assess --------------------------------------------------------------------------------------
def missing(report):
    out = [key for key in ("verdict",) if not report.get("verdict")]
    out += [] if report["meta"].get("summary") else ["summary"]
    for item in report["items"]:
        required = item["kind"] == "highlight" or item.get("general") or (item["kind"] != "patch" and item.get("match"))
        if required and not item.get("assessment"):
            out.append(item["id"])
    return out


def check_assessment(ident, value):
    if value is None:
        return None
    if not isinstance(value, dict):
        fail(f"{ident}: expected an object with affects, summary, impact, and action", 2)
    unknown = set(value) - {"affects", "summary", "impact", "action"}
    if unknown:
        fail(f"{ident}: unknown fields {sorted(unknown)}", 2)
    affects = value.get("affects", "none")
    if affects not in AFFECTS:
        fail(f"{ident}: affects must be one of {', '.join(AFFECTS)}", 2)
    clean = {"affects": affects}
    for field in ("summary", "impact", "action"):
        text = value.get(field)
        if text is not None and not isinstance(text, str):
            fail(f"{ident}: {field} must be text", 2)
        if text and text.strip():
            clean[field] = text.strip()
    if "summary" not in clean:
        fail(f"{ident}: summary is required", 2)
    if affects != "none" and "impact" not in clean:
        fail(f"{ident}: impact is required when affects is {affects}", 2)
    if affects == "action" and "action" not in clean:
        fail(f"{ident}: action is required when affects is action", 2)
    return clean


def assess(args):
    path = pathlib.Path(args.report)
    report = json.loads(path.read_text(encoding="utf-8"))
    try:
        judgments = json.load(sys.stdin)
    except ValueError as err:
        fail(f"Judgments are not valid JSON: {err}", 2)
    if not isinstance(judgments, dict):
        fail("Judgments must be a JSON object", 2)
    unknown = set(judgments) - {"items", "verdict", "summary", "author", "model"}
    if unknown:
        fail(f"Unknown top-level fields: {sorted(unknown)}", 2)
    by_id = {item["id"]: item for item in report["items"]}
    updates = {}
    for ident, value in (judgments.get("items") or {}).items():
        if ident not in by_id:
            fail(f"No item with id {ident!r} in {path}", 2)
        updates[ident] = check_assessment(ident, value)
    verdict = judgments.get("verdict")
    if verdict is not None:
        if not isinstance(verdict, dict) or verdict.get("level") not in report_render.LEVELS \
                or not str(verdict.get("reason") or "").strip():
            fail(f"verdict needs a level ({', '.join(report_render.LEVELS)}) and a reason", 2)
        report["verdict"] = {"level": verdict["level"], "reason": str(verdict["reason"]).strip()}
    for ident, value in updates.items():
        by_id[ident]["assessment"] = value
    for field in ("summary", "author", "model"):
        if judgments.get(field):
            report["meta"][field] = str(judgments[field]).strip()
    save(path, report)

    gaps = missing(report)
    if gaps:
        print(f"Saved {len(updates)} judgments to {path}. Still missing ({len(gaps)}):")
        for gap in gaps:
            print(f"- {gap}")
        sys.exit(1)
    html_path, md_path = render_files(report, path)
    print(f"HTML: {html_path}")
    print(f"Markdown: {md_path}")
    print(f"Verdict: {report_render.verdict_line(report)}")
    rank = {"action": 0, "behavior": 1, "opportunity": 2}
    relevant = [i for i in report["items"] if (i.get("assessment") or {}).get("affects") in rank]
    for item in sorted(relevant, key=lambda i: rank[i["assessment"]["affects"]]):
        a = item["assessment"]
        print(f"- {a['affects']}: [{item['title']}]({item['url']}) ({item['release']}): {a.get('action') or a['impact']}")


def render_files(report, path, html_path=None, md_path=None):
    html_path = pathlib.Path(html_path or path.with_suffix(".html"))
    md_path = pathlib.Path(md_path or path.with_suffix(".md"))
    html_path.write_text(report_render.render_html(report), encoding="utf-8")
    md_path.write_text(report_render.render_md(report), encoding="utf-8")
    return html_path, md_path


def render(args):
    path = pathlib.Path(args.report)
    report = json.loads(path.read_text(encoding="utf-8"))
    gaps = missing(report)
    if gaps:
        fail(f"{path} still needs judgments: {', '.join(gaps[:20])}{' …' if len(gaps) > 20 else ''}")
    html_path, md_path = render_files(report, path, args.html, args.md)
    print(f"HTML: {html_path}")
    print(f"Markdown: {md_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    b = commands.add_parser("build")
    b.add_argument("--ha-data")
    b.add_argument("--domains")
    b.add_argument("--target")
    b.add_argument("--from", dest="from_version")
    b.add_argument("--out-dir", default="ha-release-notes")
    b.add_argument("--todo")
    b.add_argument("--source-dir")
    b.add_argument("--no-text", action="store_true", help="leave the posts' own text out of the report")
    a = commands.add_parser("assess")
    a.add_argument("report")
    r = commands.add_parser("render")
    r.add_argument("report")
    r.add_argument("--html")
    r.add_argument("--md")
    args = parser.parse_args()
    {"build": build, "assess": assess, "render": render}[args.command](args)


if __name__ == "__main__":
    main()
