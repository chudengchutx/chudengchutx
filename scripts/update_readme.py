#!/usr/bin/env python3
"""刷新主页 README 的仓库榜单：自有仓库 / Fork 仓库各一块，均按最近更新倒序。

数据来自 GitHub API（token 取 PROFILE_TOKEN，缺省回退 GITHUB_TOKEN）。
只在内容有变化时改写 README，避免 Actions 空转提交。
"""
import json
import os
import re
import urllib.request

OWNER = "chudengchutx"
README = os.path.join(os.path.dirname(__file__), "..", "README.md")
TOKEN = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
FORK_LIMIT = 8


def fetch_repos():
    """分页拉取本人名下全部仓库（含私有），接口已按 pushed_at 倒序。"""
    out, url = [], "https://api.github.com/user/repos?type=owner&sort=pushed&per_page=100"
    while url:
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": "profile-readme-bot",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            out += json.loads(r.read())
            link = r.headers.get("Link") or ""
            url = link.split("<")[1].split(">")[0] if 'rel="next"' in link else None
    return out


def cell(repo):
    name = repo["name"]
    title = f"[{name}]({repo['html_url']})" if not repo["private"] else f"🔒 **{name}**"
    desc = (repo.get("description") or "—").replace("|", "\\|").strip()
    if len(desc) > 60:
        desc = desc[:57] + "…"
    date = (repo.get("pushed_at") or "")[:10]
    return f"| {title} | {desc} | {date} |"


def table(rows):
    if not rows:
        return "*（暂无）*"
    head = "| 仓库 | 说明 | 最近更新 |\n|---|---|---|"
    return head + "\n" + "\n".join(rows)


def splice(text, marker, content):
    """替换 START/END 标记间内容；标记不存在则整段追加到文末。"""
    pat = re.compile(rf"(<!-- {marker}:START -->\n).*?(<!-- {marker}:END -->)", re.S)
    if pat.search(text):
        return pat.sub(lambda m: m.group(1) + content + "\n" + m.group(2), text)
    return text + f"\n<!-- {marker}:START -->\n{content}\n<!-- {marker}:END -->\n"


repos = fetch_repos()
own = [r for r in repos if not r["fork"] and r["name"] != OWNER]
forks = [r for r in repos if r["fork"]][:FORK_LIMIT]

path = os.path.abspath(README)
with open(path, encoding="utf-8") as f:
    readme = f.read()

new = splice(splice(readme, "OWN_REPOS", table([cell(r) for r in own])),
             "FORKS", table([cell(r) for r in forks]))
if new == readme:
    print("榜单无变化，跳过")
else:
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    print(f"榜单已更新：自有 {len(own)} 个，fork {len(forks)} 个")
