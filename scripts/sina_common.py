"""抓取与解析共用的新浪财经地址规则。

列表页与明细页的命名规则只在这里定义一次，抓取脚本与解析脚本都从这里
导入，保证「按什么名字存」与「按什么名字读」永远一致。
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from config import SOURCE

TITLE_PATTERN = re.compile(r"^(?P<name>.+?)\((?P<code>\d{6})\)")


def list_url(code: str) -> str:
    """个股「分红送转」列表页地址。"""
    return SOURCE["list_url"].format(code=code)


def detail_cache_name(code: str, url: str, fallback: int) -> str:
    """由明细页地址推导本地缓存文件名。

    明细页地址形如 ``...ShareBonusDetail.php?stockid=600519&type=1&end_date=2026-06-22``，
    以 ``end_date`` 作为主要标识；同一日期的配股（type=2）与分红（type=1）
    通过后缀区分，缺失参数时回退到列表中的序号。
    """
    query = parse_qs(urlparse(url).query)
    end_date = query.get("end_date", [f"item{fallback:02d}"])[0]
    kind = query.get("type", ["1"])[0]
    suffix = "" if kind == "1" else f"_t{kind}"
    return f"detail_{code}_{end_date}{suffix}.html"


def parse_stock_name(html: str, code: str) -> str:
    """从列表页标题解析股票简称，失败时回退为代码。"""
    match = re.search(r"<title>(.*?)</title>", html, flags=re.S)
    if not match:
        return code
    title = re.sub(r"\s+", "", match.group(1))
    named = TITLE_PATTERN.match(title)
    return named.group("name") if named else code
