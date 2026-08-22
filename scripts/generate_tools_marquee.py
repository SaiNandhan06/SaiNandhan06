"""
Generates tools-marquee.svg from real data across a GitHub user's repos:
  - Row 1: distinct languages actually used (by total bytes, most-used first)
  - Row 2: distinct GitHub topics the user has tagged their repos with

Run manually:
    GITHUB_TOKEN=<token> python scripts/generate_tools_marquee.py
"""

import os
import requests

USERNAME = "SaiNandhan06"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {"Authorization": f"token {TOKEN}"} if TOKEN else {}
API = "https://api.github.com"

IGNORE_LANGUAGES = {"Jupyter Notebook", "Dockerfile", "Makefile", "Shell", "TeX"}

BADGE_H = 46
BADGE_GAP = 10
PADDING_X = 14
CHAR_W = 8.4  # rough monospace width estimate at font-size 14


def get_repos():
    repos, page = [], 1
    while True:
        resp = requests.get(
            f"{API}/users/{USERNAME}/repos",
            params={"per_page": 100, "page": page, "type": "owner"},
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos


def get_languages(full_name):
    resp = requests.get(f"{API}/repos/{full_name}/languages", headers=HEADERS, timeout=30)
    return resp.json() if resp.status_code == 200 else {}


def collect_languages_and_topics(repos):
    lang_totals = {}
    topic_counts = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        for lang, b in get_languages(repo["full_name"]).items():
            if lang in IGNORE_LANGUAGES:
                continue
            lang_totals[lang] = lang_totals.get(lang, 0) + b
        for topic in repo.get("topics", []) or []:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

    languages = [l for l, _ in sorted(lang_totals.items(), key=lambda kv: kv[1], reverse=True)]
    topics = [t for t, _ in sorted(topic_counts.items(), key=lambda kv: kv[1], reverse=True)]
    return languages, topics


def badge_row(items, stroke_color, y):
    """Build one row of badges as an SVG <g> string, sized to fit text, plus its total width."""
    x = 0
    parts = []
    for item in items:
        w = max(60, int(len(item) * CHAR_W) + PADDING_X * 2)
        parts.append(
            f'<rect x="{x}" y="0" width="{w}" height="{BADGE_H}" rx="10" '
            f'fill="#0f2833" stroke="{stroke_color}" stroke-opacity="0.7"/>'
            f'<text x="{x + w/2}" y="{BADGE_H/2 + 5}" text-anchor="middle" '
            f'font-family="Consolas, Menlo, monospace" font-size="14" font-weight="600" '
            f'fill="#c8e1ff">{item}</text>'
        )
        x += w + BADGE_GAP
    return "".join(parts), x  # x ends as total row width


def build_marquee_row(items, stroke_color, y_offset, dur, reverse=False):
    if not items:
        items = ["no data yet"]
    row_svg, row_width = badge_row(items, stroke_color, 0)
    dup_svg, _ = badge_row(items, stroke_color, 0)

    if reverse:
        start, end = f"-{row_width} 0", "0 0"
    else:
        start, end = "0 0", f"-{row_width} 0"

    return f'''
    <g transform="translate(30,{y_offset})">
      <g>
        <animateTransform attributeName="transform" attributeType="XML" type="translate"
                           values="{start}; {end}" dur="{dur}s" repeatCount="indefinite" calcMode="linear"/>
        <g>{row_svg}</g>
        <g transform="translate({row_width},0)">{dup_svg}</g>
      </g>
    </g>'''


def build_svg(languages, topics):
    lang_row = build_marquee_row(languages[:12], "#3a8296", 58, 22, reverse=False)
    topic_row = build_marquee_row([f"#{t}" for t in topics[:12]], "#61DAFB", 142, 26, reverse=True)

    return f'''<svg width="920" height="220" viewBox="0 0 920 220" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#091519"/>
      <stop offset="100%" stop-color="#000000"/>
    </linearGradient>
    <linearGradient id="fadeL" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#091519" stop-opacity="1"/>
      <stop offset="100%" stop-color="#091519" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="fadeR" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#000000" stop-opacity="0"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="1"/>
    </linearGradient>
    <clipPath id="clip"><rect x="0" y="0" width="920" height="220" rx="16"/></clipPath>
  </defs>

  <rect width="920" height="220" rx="16" fill="url(#bg)"/>
  <rect x="1" y="1" width="918" height="218" rx="15" fill="none" stroke="#3a8296" stroke-opacity="0.4"/>

  <text x="30" y="34" font-family="Consolas, Menlo, monospace" font-size="15" fill="#61DAFB">
    tools_used.json <tspan fill="#3a8296">— live from repo languages &amp; topics</tspan>
  </text>

  <g clip-path="url(#clip)">
    {lang_row}
    {topic_row}
    <rect x="0" y="0" width="80" height="220" fill="url(#fadeL)"/>
    <rect x="840" y="0" width="80" height="220" fill="url(#fadeR)"/>
  </g>
</svg>'''


def main():
    try:
        repos = get_repos()
        languages, topics = collect_languages_and_topics(repos)
    except requests.RequestException:
        languages, topics = [], []

    svg = build_svg(languages, topics)
    os.makedirs("assets", exist_ok=True)
    with open(os.path.join("assets", "tools-marquee.svg"), "w") as f:
        f.write(svg)

    print(f"Wrote tools-marquee.svg — {len(languages)} language(s), {len(topics)} topic(s) found.")


if __name__ == "__main__":
    main()
