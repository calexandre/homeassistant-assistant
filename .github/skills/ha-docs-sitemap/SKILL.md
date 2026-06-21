---
name: ha-docs-sitemap
description: >-
  Structured sitemap of the official Home Assistant documentation (home-assistant.io/docs/)
  and the Companion App documentation (companion.home-assistant.io/docs/).
  Provides direct links to every major section and sub-page so agents can navigate
  to the correct docs page without crawling. Use when an agent needs to find the right
  HA documentation URL for automations, scripts, scenes, blueprints, templates,
  configuration, integrations, dashboards, energy, voice assistants, companion app
  notifications, sensors, location tracking, or troubleshooting.
---

# HA Documentation Sitemap

## Quick start

Use [SITEMAP.md](SITEMAP.md) as a lookup table to find the exact documentation
URL for any Home Assistant topic. Jump directly to the relevant section instead
of crawling from the root.

## When to use

- Before fetching HA docs pages — find the correct URL first.
- When building doc links for automation/script/blueprint responses.
- When the user asks about a HA feature and you need the canonical docs page.
- Before providing any suggestion or code — this skill is the documentation core.

## Documentation research policy

- **Source of truth**: prefer the official docs over blogs or forum posts. Only reference other sources if the official docs are insufficient, and clearly label them as non-official.
- **Knowledge freshness**: your training is out of date. Do not rely on prior knowledge without verification — search and read the official docs relevant to the request first.
- **Cite exact sections**: link to the relevant doc section for any steps or code you provide. Call out version-specific behavior (e.g., breaking changes) when known.
- **Fetch, don't crawl**: use [SITEMAP.md](SITEMAP.md) to find the correct URL, then fetch the page directly. Only follow sub-links when deeper detail is needed — never crawl from the root index.
- **Avoid deprecated options** and confirm syntax against docs before answering.

## Workflow

1. Identify the user's topic (e.g., "automation triggers", "template sensors").
2. Look up the topic in [SITEMAP.md](SITEMAP.md).
3. Fetch the specific URL directly — skip the root index crawl.
4. If the topic spans multiple pages, fetch them in parallel.
5. Summarize findings and cite the exact sections used (link them).

## Sitemap structure

The sitemap is organized by top-level documentation section with nested
sub-pages. Each entry includes:

- Section name
- Direct URL
- Brief description of what the page covers

See [SITEMAP.md](SITEMAP.md) for the full reference.
