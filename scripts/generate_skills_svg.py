"""
Generates assets/skills-dashboard.svg from real language data across
all of a GitHub user's public repositories.

Run manually:
    GITHUB_TOKEN=<token> python scripts/generate_skills_svg.py

In CI, GITHUB_TOKEN is provided automatically by GitHub Actions.
"""

import os
import sys
import requests

USERNAME = "SaiNandhan06"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {"Authorization": f"token {TOKEN}"} if TOKEN else {}
API = "https://api.github.com"

# Languages to ignore (markup/config noise that isn't really a "skill")
IGNORE_LANGUAGES = {"Jupyter Notebook", "Dockerfile", "Makefile", "Shell", "TeX"}

TOP_N = 6
BAR_MAX_WIDTH = 560
ROW_HEIGHT = 40
TOP_OFFSET = 64
LEFT_LABEL_X = 30
BAR_X = 220


def get_repos():
    repos = []
    page = 1
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
    if resp.status_code != 200:
        return {}
    return resp.json()


def aggregate_languages(repos):
    totals = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        langs = get_languages(repo["full_name"])
        for lang, byte_count in langs.items():
            if lang in IGNORE_LANGUAGES:
                continue
            totals[lang] = totals.get(lang, 0) + byte_count
    return totals


def build_svg(totals):
    if not totals:
        # No data yet (empty account, or API call failed) — show a placeholder state
        svg_height = TOP_OFFSET + ROW_HEIGHT + 20
        return f'''<svg width="920" height="{svg_height}" viewBox="0 0 920 {svg_height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#091519"/>
      <stop offset="100%" stop-color="#000000"/>
    </linearGradient>
  </defs>
  <rect width="920" height="{svg_height}" rx="16" fill="url(#bg)"/>
  <rect x="1" y="1" width="918" height="{svg_height - 2}" rx="15" fill="none" stroke="#3a8296" stroke-opacity="0.4"/>
  <text x="30" y="34" font-family="Consolas, Menlo, monospace" font-size="15" fill="#61DAFB">
    skills.yaml <tspan fill="#3a8296">— waiting for first sync...</tspan>
  </text>
  <text x="30" y="80" font-family="Consolas, Menlo, monospace" font-size="13" fill="#8fd4e8">
    Push a repo or wait for the scheduled Action to run.
  </text>
</svg>'''

    sorted_langs = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
    max_bytes = sorted_langs[0][1]
    total_bytes = sum(totals.values())

    svg_height = TOP_OFFSET + ROW_HEIGHT * len(sorted_langs) + 20

    bars = []
    for i, (lang, byte_count) in enumerate(sorted_langs):
        rel_width = round(BAR_MAX_WIDTH * (byte_count / max_bytes))
        pct_of_total = round(100 * byte_count / total_bytes)
        y = TOP_OFFSET + i * ROW_HEIGHT
        label_y = y + 14
        begin = round(0.2 * (i + 1), 2)
        label_begin = round(begin + 1.4, 2)

        bars.append(f'''
    <text x="{LEFT_LABEL_X}" y="{label_y}" fill="#c8e1ff" font-family="Consolas, Menlo, monospace" font-size="13">{lang}</text>
    <rect x="{BAR_X}" y="{y}" width="{BAR_MAX_WIDTH}" height="16" rx="8" fill="#0f2833"/>
    <rect x="{BAR_X}" y="{y}" height="16" rx="8" fill="url(#barFill)" width="0">
      <animate attributeName="width" from="0" to="{rel_width}" dur="1.4s" begin="{begin}s" fill="freeze" calcMode="spline" keySplines="0.25 0.1 0.25 1"/>
    </rect>
    <text font-size="12" fill="#61DAFB" y="{label_y}" opacity="0" font-family="Consolas, Menlo, monospace">
      <animate attributeName="opacity" from="0" to="1" dur="0.4s" begin="{label_begin}s" fill="freeze"/>
      <animate attributeName="x" from="{BAR_X + 10}" to="{BAR_X + 10 + rel_width}" dur="1.4s" begin="{begin}s" fill="freeze" calcMode="spline" keySplines="0.25 0.1 0.25 1"/>
      {pct_of_total}%
    </text>''')

    bars_svg = "\n".join(bars)

    return f'''<svg width="920" height="{svg_height}" viewBox="0 0 920 {svg_height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#091519"/>
      <stop offset="100%" stop-color="#000000"/>
    </linearGradient>
    <linearGradient id="barFill" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#3a8296"/>
      <stop offset="100%" stop-color="#61DAFB"/>
    </linearGradient>
    <pattern id="grid" width="34" height="34" patternUnits="userSpaceOnUse">
      <path d="M34 0H0V34" fill="none" stroke="#61DAFB" stroke-opacity="0.03"/>
    </pattern>
  </defs>
  <rect width="920" height="{svg_height}" rx="16" fill="url(#bg)"/>
  <rect width="920" height="{svg_height}" rx="16" fill="url(#grid)"/>
  <rect x="1" y="1" width="918" height="{svg_height - 2}" rx="15" fill="none" stroke="#3a8296" stroke-opacity="0.4"/>
  <text x="30" y="34" font-family="Consolas, Menlo, monospace" font-size="15" fill="#61DAFB">
    skills.yaml <tspan fill="#3a8296">— live from GitHub repos</tspan>
  </text>
  <g>
{bars_svg}
  </g>
</svg>'''


def main():
    try:
        repos = get_repos()
        totals = aggregate_languages(repos)
    except requests.RequestException as exc:
        print(f"GitHub API call failed: {exc}", file=sys.stderr)
        totals = {}

    svg = build_svg(totals)

    os.makedirs("assets", exist_ok=True)
    out_path = os.path.join("assets", "skills-dashboard.svg")
    with open(out_path, "w") as f:
        f.write(svg)

    print(f"Wrote {out_path} — {len(totals)} language(s) detected across repos.")


if __name__ == "__main__":
    main()
