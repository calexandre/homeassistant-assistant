"""Parse a Home Assistant release post, in its Markdown source from the home-assistant.io repo, into items.

parse_post(markdown, release, url) returns {"title", "date", "url", "release", "patches", "items", "warnings"}.
Each item: {"kind", "release", "title", "anchor", "domains", "prs", "text"}, where kind is one of
highlight, new_integration, improvement, now_in_ui, removed, noteworthy, breaking, or patch. Patch
fixes carry their own release ("2026.10.2"); everything else carries the monthly one ("2026.10").

Sections are recognized by their fixed names, not their position: every other top-level section is
a highlight. Domains come from /integrations/<domain> links; a breaking change takes them from its
"[<Name> documentation]" reference first, because its body may link a replacement integration.
"""
import re

TOP_LEVEL = (  # heading prefix -> section role; any other "## " section is a highlight
    ("integrations", "integrations"), ("other noteworthy", "noteworthy"), ("patch releases", "patches"),
    ("need help", None), ("backward-incompatible", "breaking"), ("all changes", None),
)
UNDER_INTEGRATIONS = (
    ("new integrations", "new_integration"), ("noteworthy improvements", "improvement"),
    ("now available", "now_in_ui"), ("farewell", "removed"), ("integration quality", None),
)

REF_DEF = re.compile(r"^\[([^\]]+)\]:\s*(\S+)", re.M)
HEADING = re.compile(r"^(#{2,4})\s+(.+?)\s*#*\s*$")
INLINE_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)[^)]*\)")
REF_LINK = re.compile(r"\[([^\]]+)\](?:\[([^\]]*)\])?(?![(:\[])")
BOLD_LINK = re.compile(r"\*\*\[([^\]]+)\](?:\(([^)\s]+)[^)]*\)|\[([^\]]*)\])?\*\*")
DETAILS = re.compile(r"\{%\s*details\s+[\"']([^\"']+)[\"']\s*%\}(.*?)\{%\s*enddetails\s*%\}", re.S)
PATCH_HEADING = re.compile(r"^(\d{4}\.\d{1,2}\.\d+)\b")
DOMAIN = re.compile(r"^(?:https?://(?:www\.)?home-assistant\.io)?/integrations/([a-z0-9_.]+)")
PR = re.compile(r"^https://github\.com/home-assistant/[a-z0-9._-]+/pull/\d+$")


def slug(heading):
    """The anchor home-assistant.io gives a heading: lowercase, punctuation dropped, spaces to dashes."""
    text = re.sub(r"[^\w\s-]", "", heading.lower(), flags=re.U)
    return re.sub(r"\s", "-", text.strip())


def key_of(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "item"


def domain_of(url):
    match = DOMAIN.match(url or "")
    if not match:
        return None
    name = match.group(1).strip(".")
    return name.split(".")[-1] if "." in name else name  # /integrations/sensor.rest/ is the rest integration


def front_matter(text):
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    meta = {}
    for line in text[3:end].splitlines():
        if ":" in line and not line.startswith((" ", "-")):
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"')
    return meta, text[end + 4:]


class Post:
    def __init__(self, markdown):
        self.meta, body = front_matter(markdown.replace("\r\n", "\n"))
        self.refs = {}
        for label, url in REF_DEF.findall(body):
            self.refs.setdefault(label.lower(), url)
        self.body = body

    def links(self, text):
        """(label, url) for every inline and reference link in text."""
        found = [(label, url) for label, url in INLINE_LINK.findall(text)]
        stripped = INLINE_LINK.sub("", text)
        for label, ref in REF_LINK.findall(stripped):
            url = self.refs.get((ref or label).lower())
            if url:
                found.append((label, url))
        return found

    def domains(self, text):
        return unique(d for _, url in self.links(text) if (d := domain_of(url)))

    def prs(self, text):
        return unique(url for _, url in self.links(text) if PR.match(url))

    def sections(self):
        """[(level, heading, body)] for every heading outside code fences, in order."""
        out, current, fence = [], None, False
        for line in self.body.splitlines():
            if line.lstrip().startswith("```"):
                fence = not fence
            match = None if fence else HEADING.match(line)
            if match:
                current = [len(match.group(1)), match.group(2).strip(), []]
                out.append(current)
            elif current:
                current[2].append(line)
        return [(level, heading, "\n".join(lines)) for level, heading, lines in out]


def unique(values):
    seen, out = set(), []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def plain(text):
    """Readable text for the agent: Liquid tags, links, credits, and HTML reduced to their words."""
    text = REF_DEF.sub("", text)
    text = re.sub(r"\{%\s*term\s+(.*?)%\}", term_words, text)
    text = re.sub(r"\{%\s*my\s+[^%]*?title=\"([^\"]+)\"[^%]*%\}", r"\1", text)
    text = re.sub(r"\{%.*?%\}", "", text, flags=re.S)
    text = re.sub(r"\s*\((?:\[@[^\]]+\][,\s]*)+(?:-\s*)?(?:\[[^\]]*#\d+\][,\s]*)*\)", "", text)  # ([@x] - [#1])
    text = re.sub(r"\s*\(\[[^\]]+ documentation\]\)", "", text)
    text = INLINE_LINK.sub(r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", text)
    text = re.sub(r"\[([^\]]+)\](?![(:])", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("**", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def term_words(match):
    """{% term automations %} -> automations; {% term "update" "update entity" %} -> the last argument."""
    parts = re.findall(r'"([^"]*)"|(\S+)', match.group(1))
    words = [quoted or bare for quoted, bare in parts]
    return words[-1] if words else ""


def list_items(body):
    """Top-level "- " list items, with their indented continuation lines."""
    items, current = [], None
    for line in body.splitlines():
        if line.startswith("- "):
            if current is not None:
                items.append(current)
            current = line[2:]
        elif current is not None and line.startswith("  ") and line.strip():
            current += "\n" + line.strip()
        elif current is not None and line.strip():
            items.append(current)
            current = None
    if current is not None:
        items.append(current)
    return items


def role(heading, table):
    lower = heading.lower()
    for prefix, name in table:
        if lower.startswith(prefix):
            return name
    return "other"


def parse_post(markdown, release, url):
    post = Post(markdown)
    items, warnings, patches = [], [], []
    keys = set()

    def add(kind, title, anchor, text, domains=(), prs=(), item_release=None, key=None):
        rel = item_release or release
        base = f"{rel}/{kind}/{key or key_of(title)}"
        ident, n = base, 2
        while ident in keys:
            ident, n = f"{base}-{n}", n + 1
        keys.add(ident)
        items.append({"id": ident, "kind": kind, "release": rel, "title": title.strip(),
                      "url": f"{url}#{anchor}", "domains": list(domains), "prs": list(prs), "text": plain(text)})

    top, sub = None, None
    seen_breaking = False
    sections = post.sections()
    # A highlight spans its "### " subsections, so gather each top-level section's full body first.
    full = {}
    for index, (level, heading, body) in enumerate(sections):
        if level == 2:
            parts = [body]
            for lvl, head, text in sections[index + 1:]:
                if lvl == 2:
                    break
                parts.append(f"{head}\n{text}")
            full[index] = "\n".join(parts)

    for index, (level, heading, body) in enumerate(sections):
        if level == 2:
            top, sub = role(heading, TOP_LEVEL), None
            if top == "other":
                add("highlight", heading, slug(heading), full[index], post.domains(full[index]), key=slug(heading))
            elif top == "noteworthy":
                for item in list_items(body):
                    add("noteworthy", noteworthy_title(item), slug(heading), item, post.domains(item))
            elif top == "breaking":
                seen_breaking = True
                for title, block in DETAILS.findall(body):
                    add("breaking", title, slug(heading), block, breaking_domains(post, block), post.prs(block))
            continue
        if top == "integrations" and level == 3:
            sub = role(heading, UNDER_INTEGRATIONS)
            anchor = slug(heading)
            if sub == "other":
                add("noteworthy", heading, anchor, body, post.domains(body), key=anchor)
            for item in list_items(body) if sub not in ("other", None) else []:
                bold = BOLD_LINK.match(item)
                if sub == "removed":
                    # Removed integrations are named in plain bold; guess the domain from the name.
                    named = re.match(r"\*\*([^*]+)\*\*", item)
                    name = bold.group(1) if bold else named.group(1) if named else item[:60]
                    domain = domain_of(bold_url(post, bold)) if bold else None
                    short = re.findall(r"\(([A-Za-z0-9 ]+)\)", name)  # "Orange and Rockland Utility (ORU)"
                    guesses = [key_of(re.sub(r"\s*\([^)]*\)", "", name)).replace("-", "_")]
                    guesses += [key_of(s).replace("-", "_") for s in short]
                    add("removed", name, anchor, item, [domain] if domain else unique(guesses))
                elif bold:
                    links = BOLD_LINK.finditer(item) if sub == "improvement" else [bold]
                    domains = unique(d for m in links if (d := domain_of(bold_url(post, m))))
                    add(sub, bold.group(1), anchor, item, domains, key=domains[0] if domains else None)
        elif top == "noteworthy" and level == 3:
            add("noteworthy", heading, slug(heading), body, post.domains(body), key=slug(heading))
        elif top == "patches" and level == 3:
            match = PATCH_HEADING.match(heading)
            if not match:
                continue
            version = match.group(1)
            patches.append(version)
            for item in list_items(body):
                title = re.sub(r"\s*\(\[@.*$", "", item.split("\n")[0]).strip()
                prs = post.prs(item)
                key = prs[0].rsplit("/", 1)[-1] if prs else None
                add("patch", plain(title), slug(heading), item, (), prs, item_release=version, key=key)

    if not seen_breaking:
        warnings.append(f"{release}: no backward-incompatible changes section found; check the post itself")
    if not any(i["kind"] == "highlight" for i in items):
        warnings.append(f"{release}: no highlights found; the post may use a new layout")
    return {"title": post.meta.get("title", ""), "date": post.meta.get("date", "")[:10], "url": url,
            "release": release, "patches": patches, "items": items, "warnings": warnings}


def bold_url(post, match):
    if not match:
        return None
    return match.group(2) or post.refs.get((match.group(3) or match.group(1)).lower())


def noteworthy_title(item):
    bold = re.search(r"\*\*\[?([^\]*]+)\]?(?:\([^)]*\)|\[[^\]]*\])?\*\*", item)
    if bold:
        return bold.group(1)
    first = plain(item.split("\n")[0])
    return first if len(first) <= 80 else first[:77].rsplit(" ", 1)[0] + "…"


def breaking_domains(post, block):
    documented = unique(d for label, url in post.links(block)
                        if label.lower().endswith("documentation") and (d := domain_of(url)))
    return documented or post.domains(block)
