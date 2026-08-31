#!/usr/bin/env python3
"""刷新主页 README 的仓库榜单：自有仓库 / Fork 仓库各一块，均按最近更新倒序。

数据来自 GitHub API（token 取 PROFILE_TOKEN，缺省回退 GITHUB_TOKEN）。
只在内容有变化时改写 README，避免 Actions 空转提交。
"""
import os
import re
import urllib.request

OWNER = "chudengchutx"
README = os.path.join(os.path.dirname(__file__), "..", "README.md")
TOKEN = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN", "")


def fetch_repos():
    """分页拉取本人名下全部仓库（含私有），接口已按 pushed_at 倒序。"""
    out, url = [], f"https://api.github.com/user/repos?type=owner&sort=pushed&per_page=100"
    while url:
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": "profile-readme-bot",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            out += json.loads(r.read())
            url = (r.headers.get("Link") or "").split('<')[1].split('>')[0] if 'rel="next"' in r.headers.get("Link", "") else None
    return out


def cell(repo):
    name = repo["name"]
    title = f"[{name}]({repo['html_url']})" if not repo["private"] else f"🔒 **{name}**"
    desc = (repo.get("description") or "—").replace("|", "\\|").strip()
    if len(desc) > 60:
        desc = desc[:57] + "…"
    lang = repo.get("language") or "—"
    date = (repo.get("pushed_at") or "")[:10]
    return f"| {title} | {desc} | {lang} | {date} |"


def table(rows):
    if not rows:
        return "*（暂无）*"
    head = "| 仓库 | 说明 | 语言 | 最近更新 |\n|---|---|---|---|"
    return head + "\n" + "\n".join(rows)


def splice(text, marker, content):
    """替换 START/END 标记间内容；标记不存在则整段追加到文末。"""
    pat = re.compile(rf"(<!-- {marker}:START -->\n).*?(<!-- {marker}:END -->)", re.S)
    if pat.search(text):
        return pat.sub(lambda m: m.group(1) + content + "\n" + m.group(2), text)
    return text + f"\n<!-- {marker}:START -->\n{content}\n<!-- {marker}:END -->\n"


import json  # noqa: E402

repos = fetch_repos()
own = table([cell(r) for r in repos if not r["fork"]])
forks = table([cell(r) for r in repos if r["fork"]])

path = os.path.abspath(README)
with open(path, encoding="utf-8") as f:
    readme = f.read()

new = splice(splice(readme, "OWN_REPOS", own), "FORKS", forks)
if new == readme:
    print("榜单无变化，跳过")
else:
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    print(f"榜单已更新：自有 {sum(1 for r in repos if not r['fork'])} 个，fork {sum(1 for r in repos if r['fork'])} 个")
