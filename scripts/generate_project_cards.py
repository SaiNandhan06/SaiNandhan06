"""
Fetches real repos, generates a styled SVG "card" per project (so they don't
render as plain blue markdown links), and rewrites the grid of cards between
<!-- PROJECTS:START --> and <!-- PROJECTS:END --> markers in README.md.

Cards are written to assets/project-1.svg .. assets/project-N.svg (fixed slot
names, overwritten each run, so stale files never pile up if repos change).

Run manually:
    GITHUB_TOKEN=<token> python scripts/generate_project_cards.py
"""

import os
import requests

USERNAME = "SaiNandhan06"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {"Authorization": f"token {TOKEN}"} if TOKEN else {}
API = "https://api.github.com"

README_PATH = "README.md"
START_MARKER = "<!-- PROJECTS:START -->"
END_MARKER = "<!-- PROJECTS:END -->"
MAX_PROJECTS = 6
ASSETS_DIR = "assets"

LANGUAGE_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Java": "#b07219",
    "C++": "#f34b7d",
    "C": "#555555",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Jupyter Notebook": "#DA5B0B",
}
DEFAULT_COLOR = "#61DAFB"


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


def pick_projects(repos):
    candidates = [
        r for r in repos
        if not r.get("fork")
        and not r.get("archived")
        and r["name"].lower() != USERNAME.lower()
    ]
    candidates.sort(key=lambda r: (r.get("stargazers_count", 0), r.get("pushed_at", "")), reverse=True)
    return candidates[:MAX_PROJECTS]


def truncate(text, max_len):
    if not text:
        return "No description yet"
    return text if len(text) <= max_len else text[: max_len - 1].rstrip() + "…"


def build_card_svg(repo):
    name = repo["name"]
    desc = truncate(repo.get("description"), 42)
    lang = repo.get("language") or "—"
    color = LANGUAGE_COLORS.get(lang, DEFAULT_COLOR)
    stars = repo.get("stargazers_count", 0)

    return f'''<svg width="300" height="130" viewBox="0 0 300 130" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#091519"/>
      <stop offset="100%" stop-color="#000000"/>
    </linearGradient>
  </defs>
  <rect width="300" height="130" rx="14" fill="url(#bg)"/>
  <rect x="1" y="1" width="298" height="128" rx="13" fill="none" stroke="#3a8296" stroke-opacity="0.5"/>

  <text x="18" y="34" font-family="Consolas, Menlo, monospace" font-size="16" font-weight="700" fill="#61DAFB">{name}</text>

  <text x="18" y="58" font-family="Consolas, Menlo, monospace" font-size="12" fill="#8fd4e8">{desc}</text>

  <circle cx="24" cy="102" r="5" fill="{color}"/>
  <text x="36" y="106" font-family="Consolas, Menlo, monospace" font-size="12" fill="#c8e1ff">{lang}</text>

  <path d="M258,94 L260.5,99 L266,99.7 L262,103.4 L263,109 L258,106.2 L253,109 L254,103.4 L250,99.7 L255.5,99 Z" fill="#61DAFB"/>
  <text x="272" y="106" font-family="Consolas, Menlo, monospace" font-size="12" fill="#c8e1ff">{stars}</text>
</svg>'''


def write_cards(projects):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    # clear any previously-generated card slots first
    for i in range(1, MAX_PROJECTS + 1):
        path = os.path.join(ASSETS_DIR, f"project-{i}.svg")
        if os.path.exists(path):
            os.remove(path)
    for i, repo in enumerate(projects, start=1):
        with open(os.path.join(ASSETS_DIR, f"project-{i}.svg"), "w", encoding="utf-8") as f:
            f.write(build_card_svg(repo))


def build_grid_markdown(projects):
    if not projects:
        return "_No public repos found yet — add one and this section fills in automatically._"

    cells = []
    for i, repo in enumerate(projects, start=1):
        url = repo["html_url"]
        cells.append(
            f'    <td align="center">\n'
            f'      <a href="{url}" target="_blank">\n'
            f'        <img src="./assets/project-{i}.svg" width="300" alt="{repo["name"]}"/>\n'
            f'      </a>\n'
            f'    </td>'
        )

    # 2 cards per row
    rows = []
    for i in range(0, len(cells), 2):
        pair = cells[i:i + 2]
        rows.append("  <tr>\n" + "\n".join(pair) + "\n  </tr>")

    return '<table align="center">\n' + "\n".join(rows) + "\n</table>"


def update_readme(grid_md):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    start_idx = content.find(START_MARKER)
    end_idx = content.find(END_MARKER)
    if start_idx == -1 or end_idx == -1:
        raise RuntimeError(f"Markers {START_MARKER} / {END_MARKER} not found in {README_PATH}")

    new_content = (
        content[: start_idx + len(START_MARKER)]
        + "\n\n" + grid_md + "\n\n"
        + content[end_idx:]
    )
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)


def main():
    try:
        repos = get_repos()
        projects = pick_projects(repos)
    except requests.RequestException:
        projects = []

    write_cards(projects)
    grid_md = build_grid_markdown(projects)
    update_readme(grid_md)
    print(f"Wrote {len(projects)} project card(s) and updated README.md.")


if __name__ == "__main__":
    main()
