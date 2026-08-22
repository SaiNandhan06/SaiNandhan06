"""
Fetches real repos for the user, picks the most relevant ones, and rewrites
the markdown table between <!-- PROJECTS:START --> and <!-- PROJECTS:END -->
markers in README.md. Real repo names, descriptions, languages, and links —
no placeholders.

Run manually:
    GITHUB_TOKEN=<token> python scripts/update_projects_readme.py
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
        and r["name"].lower() != USERNAME.lower()  # exclude the profile repo itself
    ]
    # best repos first: stars, then recency
    candidates.sort(key=lambda r: (r.get("stargazers_count", 0), r.get("pushed_at", "")), reverse=True)
    return candidates[:MAX_PROJECTS]


def build_table(projects):
    if not projects:
        return "_No public repos found yet — add one and this section fills in automatically._"

    lines = ["| Project | Description | Language | Stars |", "|---|---|---|---|"]
    for r in projects:
        name = r["name"]
        url = r["html_url"]
        desc = (r.get("description") or "—").replace("|", "\\|")
        lang = r.get("language") or "—"
        stars = r.get("stargazers_count", 0)
        lines.append(f"| [{name}]({url}) | {desc} | {lang} | {stars} |")
    return "\n".join(lines)


def update_readme(table_md):
    with open(README_PATH, "r") as f:
        content = f.read()

    start_idx = content.find(START_MARKER)
    end_idx = content.find(END_MARKER)
    if start_idx == -1 or end_idx == -1:
        raise RuntimeError(f"Markers {START_MARKER} / {END_MARKER} not found in {README_PATH}")

    new_content = (
        content[: start_idx + len(START_MARKER)]
        + "\n\n" + table_md + "\n\n"
        + content[end_idx:]
    )

    with open(README_PATH, "w") as f:
        f.write(new_content)


def main():
    try:
        repos = get_repos()
        projects = pick_projects(repos)
    except requests.RequestException:
        projects = []

    table_md = build_table(projects)
    update_readme(table_md)
    print(f"Updated README.md Projects section with {len(projects)} repo(s).")


if __name__ == "__main__":
    main()
