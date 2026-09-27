"""可选步骤：把展示页发布到 GitHub Pages，便于他人在线查看。

站点本身零网络依赖（双击 ``site/index.html`` 即可打开），但作业验收时
对方更希望直接点开一个链接。本脚本在临时目录里组装部署内容后推送到
``gh-pages`` 分支：

* ``site/`` 的内容提到分支根目录，作为站点首页；
* ``data/`` 下可下载的数据文件一并发布，保证页面上的下载按钮可用；
* 页面里 ``../data/`` 形式的相对链接改写成站点内 ``data/``。

用法::

    python scripts/deploy_pages.py --repo https://github.com/<用户>/<仓库>.git

需要能访问 GitHub 的网络环境（必要时先设置 ``https_proxy`` 环境变量）。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from config import DATA_DIR, PROJECT_ROOT, SITE_DIR

# 发布到 Pages 的数据文件（原始页面缓存 data/raw/ 不发布）
DATA_PATTERNS = ("*.csv", "*.json", "*.xlsx")


def run_git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True)


def build_payload(target: Path) -> None:
    """把站点与数据文件组装到临时目录。"""
    shutil.copytree(SITE_DIR, target, dirs_exist_ok=True)
    data_target = target / "data"
    data_target.mkdir(parents=True, exist_ok=True)
    for pattern in DATA_PATTERNS:
        for source in DATA_DIR.glob(pattern):
            shutil.copy2(source, data_target / source.name)

    index = target / "index.html"
    html = index.read_text(encoding="utf-8")
    index.write_text(html.replace("../data/", "data/"), encoding="utf-8")

    (target / ".nojekyll").write_text("", encoding="utf-8")


def pages_url(repo: str) -> str:
    slug = repo.rstrip("/").removesuffix(".git")
    owner, name = slug.split("/")[-2:]
    return f"https://{owner}.github.io/{name}/"


def main() -> None:
    parser = argparse.ArgumentParser(description="发布展示页到 gh-pages 分支")
    parser.add_argument("--repo", required=True, help="远端仓库地址或已配置的 remote 名称")
    parser.add_argument("--branch", default="gh-pages", help="发布分支名，默认 gh-pages")
    parser.add_argument("--message", default="deploy: 发布展示页到 GitHub Pages")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="sina-dividend-lab-pages-") as tmp:
        target = Path(tmp)
        build_payload(target)

        run_git(["init", "-q", "-b", args.branch], target)
        run_git(["config", "user.name", "pages-deploy"], target)
        run_git(["config", "user.email", "pages-deploy@users.noreply.github.com"], target)
        run_git(["add", "-A"], target)
        run_git(["commit", "-q", "-m", args.message], target)
        run_git(["remote", "add", "origin", args.repo], target)
        run_git(["push", "--force", "origin", args.branch], target)

    print(f"[发布] 已推送 {args.branch} 分支；站点地址：{pages_url(args.repo)}")
    print("[发布] 若首次发布，需在仓库 Settings → Pages 选择该分支作为源。")
    print(f"[发布] 仓库根目录：{PROJECT_ROOT.name}")


if __name__ == "__main__":
    main()
