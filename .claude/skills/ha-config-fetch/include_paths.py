"""Print what a fetched Home Assistant YAML file includes, so fetch-ha-data.sh can fetch it too.

Usage: include_paths.py MIRROR REL

Reads MIRROR/REL, the local copy of <config dir>/REL, and prints one line per !include target:
"file <path>" for !include, "dir <path>" for the !include_dir_* tags. Paths are relative to the
config folder, resolved against REL's folder the way Home Assistant resolves them.

Left out: commented lines, absolute paths, paths that climb out of the config folder, hidden
paths such as .storage, anything but plain names, and secrets.yaml.
"""
import pathlib
import posixpath
import re
import sys

TAG = re.compile(r"""!(include(?:_dir_(?:list|named|merge_list|merge_named))?)\s+(?:"([^"]*)"|'([^']*)'|([^#]*))""")
SAFE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._/-]*")


def targets(text, base):
    for line in text.splitlines():
        for tag, *quoted in TAG.findall(line.split("#", 1)[0]):
            target = "".join(quoted).strip()
            if not target or target.startswith("/"):
                continue
            path = posixpath.normpath(posixpath.join(base, target))
            parts = path.split("/")
            if not SAFE.fullmatch(path) or ".." in parts or any(p.startswith(".") for p in parts):
                continue
            if tag == "include":
                if path.endswith((".yaml", ".yml")) and parts[-1] != "secrets.yaml":
                    yield "file", path
            else:
                yield "dir", path


def main():
    mirror, rel = sys.argv[1], sys.argv[2]
    text = (pathlib.Path(mirror) / rel).read_text(errors="replace")
    for kind, path in dict.fromkeys(targets(text, posixpath.dirname(rel))):
        print(kind, path)


if __name__ == "__main__":
    main()
