"""Trim a filled-in release notes report into the demo's source, demo/release-notes.json.

Drops the posts' own text (home-assistant.io content is CC BY-NC-SA, this repo is MIT), the items
the page doesn't show, and the inventory it doesn't read, keeping only the names of the
automations the shown items list.

To refresh the demo for a newer release: build the report for the made-up home that
demo_home.py writes, judge it as the skill would, then run

  demo/trim_release_report.py ha-release-notes/ha-release-<target>.json demo/release-notes.json
  demo/build.sh
"""
import json
import sys


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    report = json.load(open(sys.argv[1], encoding="utf-8"))
    shown = [i for i in report["items"] if i.get("assessment") or i["kind"] in ("breaking", "removed")]
    for item in shown:
        item.pop("text", None)
    used = {e for i in shown for e in (i.get("match") or {}).get("used_by") or []}
    logic = report.get("inventory", {}).get("logic") or {}
    report["items"] = shown
    report["inventory"] = {"source": report["inventory"]["source"], "logic": {k: v for k, v in logic.items() if k in used}}
    with open(sys.argv[2], "w", encoding="utf-8") as out:
        json.dump(report, out, ensure_ascii=False, indent=1)
        out.write("\n")


if __name__ == "__main__":
    main()
