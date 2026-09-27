"""第三步：把清洗结果打包成静态站点内嵌数据，并收集测试截图。

站点本身不发起任何网络请求：所有数据都写进 ``site/assets/data.js``，
截图复制到 ``site/assets/screenshots/``，因此双击 ``site/index.html``
即可离线查看。
"""

from __future__ import annotations

import argparse
import json
import shutil
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ASSETS_DIR, DATA_DIR, DOCS_DIR, PIPELINE_STEPS, PROJECT_ROOT, SITE_DIR, SOURCE

SHOTS_DIR = DOCS_DIR / "screenshots"
SITE_SHOTS_DIR = ASSETS_DIR / "screenshots"
TEST_REPORT = PROJECT_ROOT / "tests" / "report" / "results.json"

# 截图说明：Playwright 生成的文件名 → 页面图注
SHOT_CAPTIONS: dict[str, str] = {
    "desktop-01-hero.png": "桌面端 · 首屏与关键指标",
    "desktop-02-pipeline.png": "桌面端 · 五步实现过程",
    "desktop-03-source.png": "桌面端 · 数据源与抓取清单",
    "desktop-04-dataset.png": "桌面端 · 数据成果表格",
    "desktop-05-quality.png": "桌面端 · 数据质量报告",
    "desktop-06-charts.png": "桌面端 · 结果可视化",
    "desktop-07-tests.png": "桌面端 · 测试与截图",
    "mobile-01-hero.png": "移动端 · 首屏",
    "mobile-02-tables.png": "移动端 · 数据表格",
    "mobile-03-full.png": "移动端 · 整页长图",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def png_size(path: Path) -> tuple[int, int] | None:
    """读取 PNG 头部宽高，用于截图墙展示原始分辨率。"""
    try:
        with path.open("rb") as handle:
            header = handle.read(24)
        if header[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        width, height = struct.unpack(">II", header[16:24])
        return int(width), int(height)
    except OSError:
        return None


def collect_screenshots() -> list[dict[str, Any]]:
    """复制测试截图到站点目录，并生成图注清单。"""
    if not SHOTS_DIR.exists():
        return []
    SITE_SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    shots: list[dict[str, Any]] = []
    for path in sorted(SHOTS_DIR.glob("*.png")):
        target = SITE_SHOTS_DIR / path.name
        if path.resolve() != target.resolve():
            shutil.copy2(path, target)
        size = png_size(path)
        shots.append(
            {
                "file": f"assets/screenshots/{path.name}",
                "name": path.name,
                "caption": SHOT_CAPTIONS.get(path.name, path.stem),
                "bytes": path.stat().st_size,
                "width": size[0] if size else None,
                "height": size[1] if size else None,
            }
        )
    return shots


def collect_tests() -> dict[str, Any]:
    """读取 Playwright JSON 报告，压缩成页面需要的用例清单。

    Playwright 的报告是一棵套件树：文件套件下面还有 describe 层，用例挂在
    最内层，因此需要递归遍历才能取到全部用例。
    """
    if not TEST_REPORT.exists():
        return {"available": False, "cases": [], "stats": {}}

    report = load_json(TEST_REPORT)
    cases: list[dict[str, Any]] = []

    def walk(suite: dict[str, Any], file_name: str, groups: tuple[str, ...]) -> None:
        file_name = suite.get("file") or file_name
        title = suite.get("title", "")
        if title and title != file_name:
            groups = groups + (title,)
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                results = test.get("results", [])
                status = results[-1].get("status") if results else "unknown"
                duration = sum(int(item.get("duration", 0)) for item in results)
                cases.append(
                    {
                        "suite": file_name,
                        "title": " › ".join(groups + (spec.get("title", ""),)),
                        "project": test.get("projectName", ""),
                        "status": status,
                        "ok": bool(spec.get("ok")),
                        "duration_ms": duration,
                    }
                )
        for child in suite.get("suites", []):
            walk(child, file_name, groups)

    for suite in report.get("suites", []):
        walk(suite, "", ())

    stats = report.get("stats", {})
    total = sum(int(stats.get(key, 0)) for key in ("expected", "unexpected", "flaky", "skipped"))
    return {
        "available": True,
        "stats": {
            "total": total,
            "passed": int(stats.get("expected", 0)),
            "failed": int(stats.get("unexpected", 0)),
            "flaky": int(stats.get("flaky", 0)),
            "skipped": int(stats.get("skipped", 0)),
            "duration_ms": int(stats.get("duration", 0)),
            "start_time": stats.get("startTime", ""),
        },
        "cases": cases,
    }


def build_payload() -> dict[str, Any]:
    quality = load_json(DATA_DIR / "quality_report.json")
    manifest_path = DATA_DIR / "raw" / "manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {}

    return {
        "meta": {
            "title": "新浪财经历史分红数据获取与预处理",
            "subtitle": "基于 Codex 的数据管线实战 · 第三章作业",
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "source_name": SOURCE["name"],
            "source_home": SOURCE["home"],
            "source_license": SOURCE["license"],
            "project_root": PROJECT_ROOT.name,
        },
        "pipeline": PIPELINE_STEPS,
        "stocks": load_json(DATA_DIR / "stocks.json"),
        "dividends": load_json(DATA_DIR / "dividends.json"),
        "rights": load_json(DATA_DIR / "rights.json"),
        "yearly": load_json(DATA_DIR / "yearly.json"),
        "issues": load_json(DATA_DIR / "issues.json"),
        "quality": quality,
        "manifest": manifest,
        "screenshots": collect_screenshots(),
        "tests": collect_tests(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="生成展示站点数据文件")
    parser.add_argument("--check", action="store_true", help="只检查输入文件是否齐全")
    args = parser.parse_args()

    required = ["dividends.json", "stocks.json", "yearly.json", "issues.json", "quality_report.json"]
    missing = [name for name in required if not (DATA_DIR / name).exists()]
    if missing:
        raise SystemExit(f"缺少数据文件：{', '.join(missing)}，请先运行 scripts/preprocess.py")
    if args.check:
        print(f"[检查] 数据文件齐全：{', '.join(required)}")
        return

    payload = build_payload()
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    target = ASSETS_DIR / "data.js"
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    target.write_text(
        "// 自动生成：scripts/build_site.py（请勿手工修改）\n"
        f"window.__DIVIDEND_LAB__ = {body};\n",
        encoding="utf-8",
    )

    size_kb = target.stat().st_size / 1024
    counts = payload["quality"]["counts"]
    print(
        f"[建站] 数据已写入 {target.relative_to(PROJECT_ROOT)}（{size_kb:.1f} KB）"
        f"：分红 {counts['dividend_records']} 条 / 年度 {counts['yearly_rows']} 行 / "
        f"问题 {counts['issues']} 条 / 截图 {len(payload['screenshots'])} 张"
    )


if __name__ == "__main__":
    main()
