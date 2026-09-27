"""下载并自托管设计系统推荐字体（Poppins / Open Sans，均取 latin 子集）。

设计系统把「Poppins 标题 + Open Sans 正文」列为推荐组合。为了让展示页在
完全离线（file:// 直开、无外网）环境下仍能呈现设计效果，这里把字体文件
落到 ``site/assets/fonts/``，并生成 ``site/assets/fonts.css``。

字体来源为 Google Fonts，版权归各自作者所有（SIL Open Font License）。
脚本可重复执行：已存在的字体文件默认跳过下载。
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FONTS_DIR = PROJECT_ROOT / "site" / "assets" / "fonts"
CSS_PATH = PROJECT_ROOT / "site" / "assets" / "fonts.css"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
DISPLAY = "swap"

# 需要的字重：标题 500/600/700，正文 400/600
CSS_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=Poppins:wght@500;600;700"
    "&family=Open+Sans:wght@400;600"
    f"&display={DISPLAY}"
)

FACE_BLOCK = re.compile(
    r"/\*\s*(?P<subset>[\w-]+)\s*\*/\s*@font-face\s*\{(?P<body>[^}]+)\}", re.S
)


def blocks(css_text: str) -> list[dict[str, str]]:
    """把 CSS 拆成 @font-face 块，仅保留 latin 子集。"""
    result: list[dict[str, str]] = []
    for match in FACE_BLOCK.finditer(css_text):
        if match.group("subset") != "latin":
            continue
        body = match.group("body")
        family = re.search(r"font-family:\s*'(?P<v>[^']+)'", body)
        weight = re.search(r"font-weight:\s*(?P<v>\d+)", body)
        url = re.search(r"url\((?P<v>https://[^)]+\.woff2)\)", body)
        if family and weight and url:
            result.append(
                {
                    "family": family.group("v"),
                    "weight": weight.group("v"),
                    "url": url.group("v"),
                }
            )
    return result


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # 允许通过环境变量走本地代理（HTTPS_PROXY / https_proxy）
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        session.proxies.update({"https": proxy, "http": proxy})

    response = session.get(CSS_URL, timeout=30)
    response.raise_for_status()
    faces = blocks(response.text)
    if not faces:
        print("[字体] 未从 Google Fonts 解析到 latin 子集，退出")
        sys.exit(1)

    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "/* 自动生成：scripts/fetch_fonts.py（Google Fonts / SIL OFL） */",
    ]
    for face in faces:
        slug = face["family"].lower().replace(" ", "-")
        filename = f"{slug}-{face['weight']}-latin.woff2"
        target = FONTS_DIR / filename
        if not target.exists():
            blob = session.get(face["url"], timeout=60)
            blob.raise_for_status()
            target.write_bytes(blob.content)
            print(f"[字体] 下载 {filename}（{len(blob.content)} 字节）")
        else:
            print(f"[字体] 已存在 {filename}，跳过下载")
        lines.append(
            "\n".join(
                [
                    "@font-face {",
                    f"  font-family: '{face['family']}';",
                    "  font-style: normal;",
                    f"  font-weight: {face['weight']};",
                    f"  font-display: {DISPLAY};",
                    f"  src: url('./fonts/{filename}') format('woff2');",
                    "}",
                ]
            )
        )

    CSS_PATH.write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    print(f"[字体] 共 {len(faces)} 个字重，@font-face 写入 {CSS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
