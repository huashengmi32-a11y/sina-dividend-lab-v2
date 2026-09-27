"""第一步：抓取新浪财经「分红送转」列表页与「分红明细」页。

设计要点：

* 抓取与解析解耦：原始 HTML 全量落地到 ``data/raw/``，解析失败可反复重跑，
  不会再次打扰数据源；
* 礼貌抓取：会话复用、请求间固定间隔、失败按指数退避重试；
* 全程留痕：``data/raw/manifest.json`` 记录每条请求的状态码、字节数、
  SHA-256 与耗时，作为数据来源的可追溯凭证。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from config import FETCH, RAW_DIR, SOURCE, TARGET_STOCKS
from sina_common import detail_cache_name, list_url, parse_stock_name


@dataclass
class FetchLog:
    """单次请求的留痕信息。"""

    index: int
    url: str
    file: str
    status: int
    bytes: int
    sha256: str
    elapsed_ms: int
    from_cache: bool
    fetched_at: str


@dataclass
class StockSummary:
    """单只股票的抓取小结。"""

    code: str
    name: str
    list_url: str
    detail_pages: int
    files: list[str] = field(default_factory=list)


class SinaFetcher:
    """带本地缓存、限速与重试的新浪财经抓取器。"""

    def __init__(
        self,
        raw_dir: Path = RAW_DIR,
        *,
        delay: float = FETCH["delay_seconds"],
        timeout: int = FETCH["timeout"],
        retries: int = FETCH["retries"],
        force: bool = False,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.timeout = timeout
        self.retries = retries
        self.force = force
        self.logs: list[FetchLog] = []
        self.stocks: list[StockSummary] = []

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": FETCH["user_agent"],
                "Referer": SOURCE["referer"],
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        )

    # ---------------------------------------------------------------- 基础抓取
    def fetch(self, url: str, cache_name: str) -> str:
        """抓取单个页面；命中缓存时直接读取本地文件，不发起网络请求。"""
        path = self.raw_dir / cache_name
        if path.exists() and not self.force:
            text = path.read_text(encoding="utf-8")
            self._log(url, path, status=200, size=path.stat().st_size, elapsed=0,
                      cached=True, digest=hashlib.sha256(path.read_bytes()).hexdigest())
            return text

        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            started = time.perf_counter()
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
            except requests.RequestException as exc:
                last_error = exc
                if attempt == self.retries:
                    raise RuntimeError(f"抓取失败：{url}（{exc}）") from exc
                time.sleep(self.delay * (2 ** (attempt - 1)))  # 指数退避
                continue

            elapsed_ms = int((time.perf_counter() - started) * 1000)
            text = response.content.decode(SOURCE["encoding"], errors="replace")
            path.write_text(text, encoding="utf-8")
            self._log(
                url,
                path,
                status=response.status_code,
                size=len(response.content),
                elapsed=elapsed_ms,
                cached=False,
                digest=hashlib.sha256(response.content).hexdigest(),
            )
            time.sleep(self.delay)  # 礼貌抓取：请求之间留出间隔
            return text

        raise RuntimeError(f"抓取失败：{url}") from last_error  # pragma: no cover

    def _log(
        self,
        url: str,
        path: Path,
        *,
        status: int,
        size: int,
        elapsed: int,
        cached: bool,
        digest: str,
    ) -> None:
        self.logs.append(
            FetchLog(
                index=len(self.logs) + 1,
                url=url,
                file=str(path.relative_to(self.raw_dir.parent.parent)).replace("\\", "/"),
                status=status,
                bytes=size,
                sha256=digest,
                elapsed_ms=elapsed,
                from_cache=cached,
                fetched_at=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            )
        )

    # ---------------------------------------------------------------- 页面解析
    @staticmethod
    def detail_links(list_html: str, base_url: str) -> list[str]:
        """从列表页提取全部分红 / 配股明细页链接（保持页面顺序、去重）。"""
        from urllib.parse import urljoin

        soup = BeautifulSoup(list_html, "lxml")
        links: list[str] = []
        seen: set[str] = set()
        for table_id in ("sharebonus_1", "sharebonus_2"):
            table = soup.find("table", id=table_id)
            if table is None:
                continue
            for anchor in table.find_all("a", href=True):
                link = urljoin(base_url, anchor["href"])
                if "ShareBonusDetail" in link and link not in seen:
                    seen.add(link)
                    links.append(link)
        return links

    # ------------------------------------------------------------------ 任务
    def fetch_stock(self, code: str) -> StockSummary:
        """抓取单只股票的列表页及其全部分红 / 配股明细页。"""
        url = list_url(code)
        list_html = self.fetch(url, f"list_{code}.html")
        name = parse_stock_name(list_html, code)

        detail_urls = self.detail_links(list_html, url)
        files = [f"data/raw/list_{code}.html"]
        for index, detail_url in enumerate(detail_urls, start=1):
            cache_name = detail_cache_name(code, detail_url, index)
            self.fetch(detail_url, cache_name)
            files.append(f"data/raw/{cache_name}")

        summary = StockSummary(
            code=code,
            name=name,
            list_url=url,
            detail_pages=len(detail_urls),
            files=files,
        )
        self.stocks.append(summary)
        return summary

    # ---------------------------------------------------------------- 落盘
    def write_manifest(self, *, started_at: str, elapsed_seconds: float) -> Path:
        network = [log for log in self.logs if not log.from_cache]
        manifest = {
            "source": SOURCE["name"],
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "started_at": started_at,
            "elapsed_seconds": round(elapsed_seconds, 2),
            "settings": {
                "delay_seconds": self.delay,
                "timeout_seconds": self.timeout,
                "retries": self.retries,
                "user_agent": FETCH["user_agent"],
            },
            "summary": {
                "pages": len(self.logs),
                "network_requests": len(network),
                "cache_hits": len(self.logs) - len(network),
                "total_bytes": sum(log.bytes for log in self.logs),
                "detail_pages": sum(stock.detail_pages for stock in self.stocks),
            },
            "stocks": [asdict(stock) for stock in self.stocks],
            "requests": [asdict(log) for log in self.logs],
        }
        path = self.raw_dir / "manifest.json"
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return path


def main() -> None:
    parser = argparse.ArgumentParser(description="抓取新浪财经历史分红数据")
    parser.add_argument("--force", action="store_true", help="忽略本地缓存，强制重新抓取")
    parser.add_argument("--codes", nargs="*", help="仅抓取指定股票代码，默认使用配置中的目标清单")
    parser.add_argument("--delay", type=float, default=FETCH["delay_seconds"],
                        help="请求间隔秒数，默认取配置值")
    args = parser.parse_args()

    codes = args.codes or [item["code"] for item in TARGET_STOCKS]
    started_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    started = time.perf_counter()

    fetcher = SinaFetcher(force=args.force, delay=args.delay)
    for code in codes:
        info = fetcher.fetch_stock(code)
        print(f"[抓取] {info.code} {info.name}：列表页 1 个，明细页 {info.detail_pages} 个")

    manifest = fetcher.write_manifest(
        started_at=started_at, elapsed_seconds=time.perf_counter() - started
    )
    network_hits = sum(1 for log in fetcher.logs if not log.from_cache)
    print(f"[完成] 共存档 {len(fetcher.logs)} 个页面，其中联网请求 {network_hits} 次")
    print(f"[完成] 抓取清单：{manifest}")


if __name__ == "__main__":
    main()
