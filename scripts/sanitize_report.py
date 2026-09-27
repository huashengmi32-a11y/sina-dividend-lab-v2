"""第四步（提交前）：把 Playwright 报告里的本机绝对路径替换成占位符。

Playwright 生成的 ``results.json`` 与 HTML 报告会写入本机绝对路径
（项目根目录、node_modules 等），直接提交会把本机用户名带进仓库。
本脚本按作业的脱敏要求，把这些路径统一替换为 ``<项目根目录>``。

用法::

    python scripts/sanitize_report.py
"""

from __future__ import annotations

from pathlib import Path

from config import PROJECT_ROOT

PLACEHOLDER = "<项目根目录>"
TARGETS = (
    PROJECT_ROOT / "tests" / "report" / "results.json",
    PROJECT_ROOT / "tests" / "report" / "index.html",
)


def path_variants() -> list[str]:
    """同一个路径在报告里有三种写法：原样、正斜杠、JSON 转义反斜杠。"""
    raw = str(PROJECT_ROOT)
    variants = [raw, PROJECT_ROOT.as_posix(), raw.replace("\\", "\\\\")]
    return sorted(set(variants), key=len, reverse=True)


def sanitize(path: Path) -> None:
    if not path.exists():
        print(f"[脱敏] 跳过（文件不存在）：{path.name}")
        return
    text = path.read_text(encoding="utf-8")
    original = text
    for variant in path_variants():
        text = text.replace(variant, PLACEHOLDER)
    if text == original:
        print(f"[脱敏] {path.name} 不含本机路径，未改动")
        return
    path.write_text(text, encoding="utf-8")
    print(f"[脱敏] {path.name} 已替换本机路径为 {PLACEHOLDER}")


def main() -> None:
    for target in TARGETS:
        sanitize(target)


if __name__ == "__main__":
    main()
