"""Render a release notes report (the JSON release_notes.py builds and the agent fills in) as one
offline HTML page and as Markdown with the front matter the reports have always carried.

Both show the same sections in the same order: the verdict, then what needs action, what the
user will notice, the highlights, what is worth a look, the improvements to integrations the home
uses, and one line for each breaking change or removal that does not affect it. The posts' own
text never appears; only titles, links, and the agent's words do.
"""
import html
import json
import pathlib
import re

LEVELS = {
    "upgrade": ("✅", "Upgrade"),
    "check": ("ℹ️", "Upgrade and check"),
    "review": ("⚠️", "Review first"),
    "wait": ("⏳", "Wait for a patch"),
    "hold": ("🛑", "Hold"),
}
KIND_LABEL = {
    "highlight": "Highlight", "new_integration": "New integration", "improvement": "Improvement",
    "now_in_ui": "Now in the UI", "removed": "Removed", "noteworthy": "Noteworthy", "breaking": "Breaking change",
    "patch": "Patch fix",
}
SECTIONS = (  # key, emoji, title, open by default
    ("action", "⚠️", "Needs your action", True),
    ("behavior", "ℹ️", "You'll notice", True),
    ("highlights", "✨", "Highlights", True),
    ("opportunity", "💡", "Worth a look", True),
    ("improvements", "🔧", "Improvements to your integrations", False),
    ("unaffected", "✅", "Doesn't affect you", False),
)
TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / "assets" / "template.html"
WEB = re.compile(r"https?://")


def affects(item):
    return (item.get("assessment") or {}).get("affects")


def release_key(release):
    parts = [int(p) for p in release.split(".")]
    return parts[0], parts[1], parts[2] if len(parts) > 2 else 0


def sections(report):
    order = {item["id"]: n for n, item in enumerate(report["items"])}
    by = lambda picked: sorted(picked, key=lambda i: (release_key(i["release"]), order[i["id"]]))
    items = report["items"]
    picked = {
        "action": [i for i in items if affects(i) == "action"],
        "behavior": [i for i in items if affects(i) == "behavior"],
        "highlights": [i for i in items if i["kind"] == "highlight" and affects(i) not in ("action", "behavior")],
        "opportunity": [i for i in items if affects(i) == "opportunity" and i["kind"] != "highlight"],
        "improvements": [i for i in items if i["kind"] in ("improvement", "now_in_ui", "noteworthy")
                         and i.get("match") and affects(i) in (None, "none")],
        "unaffected": [i for i in items if i["kind"] in ("breaking", "removed") and affects(i) in (None, "none")],
    }
    return [(key, emoji, title, is_open, by(picked[key])) for key, emoji, title, is_open in SECTIONS if picked[key]]


def span(report):
    meta = report["meta"]
    return f"{meta['installed']} → {meta['target']}" if meta.get("installed") else meta["target"]


def verdict_line(report):
    emoji, label = LEVELS[report["verdict"]["level"]]
    return f"{emoji} {label}: {report['verdict']['reason']}"


def used_by(report, item):
    logic = report.get("inventory", {}).get("logic") or {}
    return [logic.get(eid, eid) for eid in (item.get("match") or {}).get("used_by") or []]


# --- HTML ----------------------------------------------------------------------------------------
def esc(text):
    return html.escape(str(text), quote=True)


def inline(text):
    """Escape agent text, keeping `code` and [links](https://…)."""
    out = []
    for n, part in enumerate(re.split(r"`([^`]+)`", str(text))):
        if n % 2:
            out.append(f"<code>{esc(part)}</code>")
            continue
        pos = 0
        for match in re.finditer(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", part):
            out.append(esc(part[pos:match.start()]))
            out.append(f'<a href="{esc(match.group(2))}">{esc(match.group(1))}</a>')
            pos = match.end()
        out.append(esc(part[pos:]))
    return "".join(out)


def link(item, html=True):
    """The item's title, linked to its post only when the address is http(s)."""
    url = str(item.get("url") or "")
    if not WEB.match(url):
        return esc(item["title"]) if html else item["title"]
    if html:
        return f'<a href="{esc(url)}">{esc(item["title"])}</a>'
    title = item["title"].replace("[", "\\[").replace("]", "\\]")
    return f"[{title}]({md_url(url)})"


def html_item(report, item):
    a = item.get("assessment") or {}
    tags = [f'<span class="tag release">{esc(item["release"])}</span>',
            f'<span class="tag kind">{esc(KIND_LABEL[item["kind"]])}</span>']
    if affects(item) == "opportunity":
        tags.append('<span class="tag idea">💡 Worth a look</span>')
    tags += [f'<span class="tag domain">{esc(d)}</span>' for d in (item.get("match") or {}).get("domains") or []]
    parts = [f'<article class="item" data-affects="{esc(affects(item) or "none")}">',
             f'<h3>{link(item)}</h3>',
             f'<div class="tags">{"".join(tags)}</div>']
    if a.get("summary"):
        parts.append(f'<p class="summary">{inline(a["summary"])}</p>')
    if a.get("impact"):
        parts.append(f'<p class="impact"><b>For your setup</b> {inline(a["impact"])}</p>')
    if a.get("action"):
        parts.append(f'<p class="do"><b>Do this</b> {inline(a["action"])}</p>')
    names = used_by(report, item)
    if names and affects(item) in ("action", "behavior"):
        shown = "".join(f"<li>{esc(n)}</li>" for n in names[:12])
        more = f"<li>and {len(names) - 12} more</li>" if len(names) > 12 else ""
        parts.append(f'<div class="used"><b>Used by</b><ul>{shown}{more}</ul></div>')
    parts.append("</article>")
    return "\n".join(parts)


def html_line(item):
    return (f'<li>{link(item)} '
            f'<span class="tag release">{esc(item["release"])}</span> '
            f'<span class="muted">{esc(KIND_LABEL[item["kind"]])}</span></li>')


def render_html(report):
    meta, verdict = report["meta"], report["verdict"]
    emoji, label = LEVELS[verdict["level"]]
    body = [f'<section class="verdict level-{esc(verdict["level"])}" aria-label="Verdict">',
            f'<div class="verdict-emoji" aria-hidden="true">{emoji}</div>',
            f'<div><p class="verdict-label">{esc(label)}</p><p class="verdict-reason">{inline(verdict["reason"])}</p></div>',
            "</section>"]
    for note in meta.get("notes") or []:
        body.append(f'<p class="note">{inline(note)}</p>')
    blocks = sections(report)
    counts = {key: len(found) for key, _, _, _, found in blocks}
    if not counts.get("action") and not counts.get("behavior"):
        body.append('<p class="calm">Nothing in these releases needs your attention.</p>')
    for key, emoji, title, is_open, found in blocks:
        body.append(f'<details class="section" data-section="{key}"{" open" if is_open else ""}>')
        body.append(f'<summary><h2><span aria-hidden="true">{emoji}</span> {esc(title)} '
                    f'<span class="count">{len(found)}</span></h2></summary>')
        if key == "unaffected":
            body.append('<ul class="lines">' + "\n".join(html_line(i) for i in found) + "</ul>")
        else:
            body.append('<div class="items">' + "\n".join(html_item(report, i) for i in found) + "</div>")
        body.append("</details>")

    sources = "".join(f'<li>{link({"url": p["url"], "title": p["title"] or p["release"]})}</li>'
                      for p in report["posts"])
    byline = " · ".join(esc(x) for x in (f"Generated {meta['generated']}", meta.get("model"), meta.get("author")) if x)
    page = TEMPLATE.read_text(encoding="utf-8")
    values = {
        "__TITLE__": esc(f"Home Assistant {span(report)}"),
        "__SUMMARY__": inline(meta.get("summary") or ""),
        "__BYLINE__": byline,
        "__BODY__": "\n".join(body),
        "__SOURCES__": sources,
        "__COUNT_MINE__": str(counts.get("action", 0) + counts.get("behavior", 0)),
    }
    return re.sub("|".join(values), lambda m: values[m.group(0)], page)


# --- Markdown ------------------------------------------------------------------------------------
def one_line(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def md_url(url):
    """Percent-encode what would end or break a Markdown link target."""
    return re.sub(r"[()<>\s]", lambda m: f"%{ord(m.group(0)):02X}", url)


MD_LINK = re.compile(r"\[([^\]]*)\]\(\s*<?((?:[^()<>\s]|\([^()\s]*\))*)>?(?:\s+\"[^\"]*\")?\s*\)")
MD_AUTOLINK = re.compile(r"<([a-zA-Z][\w+.-]*:[^<>\s]*)>")


def md_text(text):
    """Agent text on one line, keeping only links to http(s), as the HTML does. `code` stays as written."""
    parts = re.split(r"(`[^`]+`)", one_line(text))
    for n in range(0, len(parts), 2):
        part = MD_LINK.sub(lambda m: m.group(0) if WEB.match(m.group(2)) else m.group(1), parts[n])
        part = MD_AUTOLINK.sub(lambda m: m.group(0) if WEB.match(m.group(1)) else m.group(1), part)
        # Whatever link the patterns above could not parse loses the "](" that makes it one.
        parts[n] = re.sub(r"\]\((?!\s*<?https?://)", "] (", part)
    return "".join(parts)


def render_md(report):
    meta = report["meta"]
    emoji, label = LEVELS[report["verdict"]["level"]]
    # The title lives in the front matter, so the body starts at H2 (.github/instructions/markdown.instructions.md).
    lines = ["---", f"title: {json.dumps(f'🏠 Home Assistant {span(report)}', ensure_ascii=False)}",
             f"author: {json.dumps(meta.get('author') or '')}", "categories:", "  - home-assistant",
             "  - release-notes", "tags:", f"  - ha-{meta['target']}", f"model: {json.dumps(meta.get('model') or '')}",
             f"summary: {json.dumps(one_line(meta.get('summary') or ''), ensure_ascii=False)}",
             f"date: {json.dumps(meta['generated'])}", "---", "",
             f"## {emoji} {label}", "", md_text(report["verdict"]["reason"]), ""]
    for note in meta.get("notes") or []:
        lines += [f"> {md_text(note)}", ""]
    for key, s_emoji, title, _, found in sections(report):
        lines += [f"## {s_emoji} {title}", ""]
        if key == "unaffected":
            lines += [f"- {link(i, html=False)} · {i['release']} · {KIND_LABEL[i['kind']]}" for i in found] + [""]
            continue
        for item in found:
            a = item.get("assessment") or {}
            lines += [f"### {link(item, html=False)} · {item['release']} · {KIND_LABEL[item['kind']]}", ""]
            label_new = "What's new" if item["kind"] == "highlight" else "What changed"
            if a.get("summary"):
                lines.append(f"- **{label_new}**: {md_text(a['summary'])}")
            if a.get("impact"):
                lines.append(f"- **For your setup**: {md_text(a['impact'])}")
            if a.get("action"):
                lines.append(f"- **Do this**: {md_text(a['action'])}")
            names = used_by(report, item)
            if names and affects(item) in ("action", "behavior"):
                lines.append(f"- **Used by**: {', '.join(names[:12])}{f' and {len(names) - 12} more' if len(names) > 12 else ''}")
            lines.append("")
    lines += ["## 📚 Sources", ""] + [f"- {link({'url': p['url'], 'title': p['title'] or p['release']}, html=False)}"
                                     for p in report["posts"]]
    return "\n".join(lines).rstrip() + "\n"
