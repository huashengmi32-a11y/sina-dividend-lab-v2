"""第二步：解析、清洗与校验新浪财经历史分红数据。

流程：读取原始 HTML → 抽取三张表（分红列表 / 配股列表 / 分红明细）→
清洗与类型转换 → 派生字段 → 10 条质量规则校验 → 去重 →
输出 CSV / JSON / Excel / 质量报告。

所有清洗规则都在 ``CHECKS`` 中显式声明，脚本本身就是处理说明书。
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup

from config import (
    DATA_DIR,
    DIVIDEND_COLUMNS,
    FIELD_DESCRIPTIONS,
    FIELD_LABELS,
    ISSUES_LABELS,
    NULL_TOKENS,
    RAW_DIR,
    RIGHTS_COLUMNS,
    RIGHTS_LABELS,
    SOURCE,
    STOCKS_COLUMNS,
    STOCKS_LABELS,
    TARGET_STOCKS,
    YEARLY_COLUMNS,
    YEARLY_LABELS,
)
from sina_common import detail_cache_name, list_url, parse_stock_name

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NUMBER_PATTERN = re.compile(r"^-?\d+(?:\.\d+)?$")

# 源站对未知公告日期使用 1900-01-01 占位；早于该阈值的日期一律视为脏数据
EARLIEST_REASONABLE_ANNOUNCE_DATE = "1990-01-01"
MAX_PER10_VALUE = 100.0          # 每 10 股送转派数值的合理上界
DETAIL_TOLERANCE = 0.01          # 列表页与明细页派息的允许差额（元）

# 列表页表格列顺序（数据行以公告日期开头）
DIVIDEND_LIST_FIELDS = [
    "announce_date", "bonus_share_per10", "transfer_share_per10",
    "cash_per10_pretax", "status", "ex_dividend_date", "record_date",
    "bonus_listing_date",
]
RIGHTS_LIST_FIELDS = [
    "announce_date", "rights_per10", "rights_price", "base_share_capital",
    "ex_rights_date", "record_date", "payment_start", "payment_end",
    "listing_date", "raised_funds",
]

# 所有需要按 yyyy-mm-dd 校验的日期字段（含配股表字段）
DATE_FIELDS = (
    "announce_date", "ex_dividend_date", "record_date", "bonus_listing_date",
    "shareholders_meeting_date", "dividend_pay_date",
    "ex_rights_date", "payment_start", "payment_end", "listing_date",
)
NUMERIC_FIELDS = (
    "bonus_share_per10", "transfer_share_per10", "cash_per10_pretax",
    "cash_per_share_pretax", "detail_cash_pretax", "detail_cash_aftertax",
)
BOOLEAN_FIELDS = (
    "announce_date_suspect", "has_cash", "has_bonus_share", "has_transfer_share",
)

# 明细页中文标签（规范化后）→ 目标字段：用「包含关键词」匹配，容错空格与括号差异
DETAIL_SPECS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "detail_cash_pretax": (("税前红利",), ("B股", "H股")),
    "detail_cash_aftertax": (("税后红利",), ("B股", "H股")),
    "shareholders_meeting_date": (("股东大会决议公告",), ()),
    "dividend_pay_date": (("红利/配股起始日",), ()),
}

# 10 条数据质量规则：既用于逐条打标，也汇总进质量报告
CHECKS = [
    {"id": "R1", "name": "关键字段完整性", "level": "error",
     "description": "股票代码与公告日期必须存在且可解析"},
    {"id": "R2", "name": "方案内容有效性", "level": "warning",
     "description": "送股、转增、派息三项至少一项大于 0；三项均为 0 或缺失视为空方案"},
    {"id": "R3", "name": "除权除息日不早于公告日", "level": "error",
     "description": "实施类方案的除权除息日必须晚于或等于公告日"},
    {"id": "R4", "name": "先登记后除权", "level": "error",
     "description": "股权登记日不得晚于除权除息日"},
    {"id": "R5", "name": "数值非负", "level": "error",
     "description": "送股、转增、派息等比例字段不允许出现负值"},
    {"id": "R6", "name": "数值上界合理性", "level": "warning",
     "description": f"每 10 股送股 / 转增 / 派息不应超过 {MAX_PER10_VALUE:g}，超出需人工复核"},
    {"id": "R7", "name": "明细页与列表页交叉校验", "level": "warning",
     "description": f"明细页税前红利与列表页派息差额不得超过 {DETAIL_TOLERANCE} 元（舍入容差）"},
    {"id": "R8", "name": "主键唯一", "level": "error",
     "description": "同一股票下公告日期不重复，重复记录清理后保留一条"},
    {"id": "R9", "name": "公告日期合理性", "level": "info",
     "description": f"公告日期不得早于 {EARLIEST_REASONABLE_ANNOUNCE_DATE}；源站以 1900-01-01 表示未知日期，命中项保留记录但不派生年度"},
    {"id": "R10", "name": "日期字段可解析", "level": "error",
     "description": "所有非空日期字段必须符合 yyyy-mm-dd 格式"},
]

NOTES = [
    "「分红年度」「分配类型」为推断字段：公告月份不超过 8 月归入上一年度分配，"
    "9 月及以后归入本期中期 / 特别分配，仅用于分组统计，不代表公司官方口径。",
    "「派息(税前)(元/10股)」与明细页「税前红利」为两套页面口径，"
    "清洗后保留双方数值并用 R7 做交叉校验。",
    "源站以 1900-01-01 表示未知公告日期，命中 R9 的记录保留原始信息，"
    "但不参与分红年度派生与累计派息统计。",
    "R6 数值上界用于拦截明显的录入错误；贵州茅台等高价股每 10 股派息可超过 100 元，"
    "命中该规则属正常业务形态，需结合股价与股本结构判断。",
    "R7 交叉校验发现列表页与明细页派息不一致时，两套数值都会保留，"
    "累计派息按列表页口径计算，问题清单中可追溯到具体记录。",
    "缺失值统一为 JSON null / CSV 空单元格，不使用 NaN、-- 等源站占位符。",
]


# ---------------------------------------------------------------- 通用清洗
def clean_text(value: Any) -> str | None:
    """空白归一化；源站占位符（--、暂无等）统一转为 None。"""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = re.sub(r"[\s\u3000]+", " ", str(value)).strip()
    if text in NULL_TOKENS:
        return None
    return text


def to_number(value: Any) -> float:
    """把源站文本转为浮点数；无法解析或缺失时返回 NaN。"""
    text = clean_text(value)
    if text is None:
        return float("nan")
    text = text.replace(",", "").replace("，", "").rstrip("%")
    if not NUMBER_PATTERN.match(text):
        return float("nan")
    number = float(text)
    return number if math.isfinite(number) else float("nan")


def normalize_date(value: Any) -> str | None:
    """日期字段标准化：可解析的保留 ISO 形式，非法值原样保留交给 R10 标记。"""
    text = clean_text(value)
    if text is None:
        return None
    return text


def normalize_label(text: str) -> str:
    """明细页标签归一：去掉空白，全角括号转半角。"""
    return (
        re.sub(r"[\s\u3000]+", "", text)
        .replace("（", "(")
        .replace("）", ")")
    )


def pick_detail(pairs: dict[str, str | None], includes: tuple[str, ...],
                excludes: tuple[str, ...]) -> str | None:
    """在明细页键值对中按关键词挑选字段。"""
    for key, value in pairs.items():
        if all(token in key for token in includes) and not any(token in key for token in excludes):
            return value
    return None


# ---------------------------------------------------------------- 表格解析
def parse_detail_page(html: str) -> dict[str, str | None]:
    """解析分红明细页的「标签 - 取值」表。"""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id="sharebonusdetail")
    pairs: dict[str, str | None] = {}
    if table is None:
        return pairs
    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        label = normalize_label(cells[0].get_text(" ", strip=True))
        if not label:
            continue
        pairs[label] = clean_text(cells[1].get_text(" ", strip=True))
    return pairs


def parse_list_rows(html: str, base_url: str, table_id: str,
                    fields: list[str]) -> list[dict[str, Any]]:
    """解析列表页数据行，同时保留每行对应的明细页链接。"""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id=table_id)
    if table is None:
        return []

    rows: list[dict[str, Any]] = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < len(fields):
            continue
        values = [clean_text(cell.get_text(" ", strip=True)) for cell in cells]
        if values[0] is None or not DATE_PATTERN.match(values[0] or ""):
            continue  # 表头与说明行

        record = {field: value for field, value in zip(fields, values)}
        anchor = tr.find("a", href=True)
        record["detail_url"] = urljoin(base_url, anchor["href"]) if anchor else None
        rows.append(record)
    return rows


def read_detail(raw_dir: Path, code: str, url: str | None, fallback: int) -> dict[str, str | None]:
    """读取并解析某条记录对应的明细页；缺失时返回空字典。"""
    if not url:
        return {}
    path = raw_dir / detail_cache_name(code, url, fallback)
    if not path.exists():
        return {}
    return parse_detail_page(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 记录构建
def build_dividend_frame(raw_dir: Path, code: str, name: str) -> pd.DataFrame:
    """把单只股票的分红列表页 + 明细页整理成结构化 DataFrame。"""
    list_path = raw_dir / f"list_{code}.html"
    if not list_path.exists():
        raise FileNotFoundError(f"缺少列表页缓存：{list_path}，请先运行 scripts/fetch_sina.py")

    html = list_path.read_text(encoding="utf-8")
    rows = parse_list_rows(html, list_url(code), "sharebonus_1", DIVIDEND_LIST_FIELDS)

    records: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        detail = read_detail(raw_dir, code, row.get("detail_url"), index)
        record: dict[str, Any] = {
            "stock_code": code,
            "stock_name": name,
            **{field: row.get(field) for field in DIVIDEND_LIST_FIELDS},
            "source_url": row.get("detail_url") or list_url(code),
        }
        for field, (includes, excludes) in DETAIL_SPECS.items():
            record[field] = pick_detail(detail, includes, excludes)
        records.append(record)

    frame = pd.DataFrame(records, columns=[
        "stock_code", "stock_name", "announce_date", "bonus_share_per10",
        "transfer_share_per10", "cash_per10_pretax", "status", "ex_dividend_date",
        "record_date", "bonus_listing_date", "detail_cash_pretax",
        "detail_cash_aftertax", "shareholders_meeting_date", "dividend_pay_date",
        "source_url",
    ])

    for column in ("stock_code", "stock_name", "status", "source_url"):
        frame[column] = frame[column].map(clean_text)
    for column in NUMERIC_FIELDS:
        if column not in frame.columns:
            frame[column] = None
        frame[column] = frame[column].map(to_number)
    for column in DATE_FIELDS:
        if column in ("ex_rights_date", "payment_start", "payment_end", "listing_date"):
            continue  # 配股表字段，不属于分红记录
        if column not in frame.columns:
            frame[column] = None
        frame[column] = frame[column].map(normalize_date)

    # 送股 / 转增缺失按 0 处理（源站常见写法），派息缺失保留 NaN
    frame["bonus_share_per10"] = frame["bonus_share_per10"].fillna(0.0)
    frame["transfer_share_per10"] = frame["transfer_share_per10"].fillna(0.0)

    # ---- 派生字段 ----
    announce = pd.to_datetime(frame["announce_date"], format="%Y-%m-%d", errors="coerce")
    frame["announce_date_suspect"] = (
        announce.notna() & (frame["announce_date"] < EARLIEST_REASONABLE_ANNOUNCE_DATE)
    )
    suspect_offset = pd.DateOffset(years=1)
    year_shift = announce - suspect_offset
    dividend_year = year_shift.dt.year.where(announce.dt.month <= 8, announce.dt.year)
    frame["dividend_year"] = (
        dividend_year.where(~frame["announce_date_suspect"]).astype("Int64")
    )
    frame["allocation_type"] = pd.Series(
        ["中期分配" if month >= 9 else "年度分配" for month in announce.dt.month.fillna(0)],
        index=frame.index,
    ).where(announce.notna() & ~frame["announce_date_suspect"])
    ex_year = pd.to_datetime(frame["ex_dividend_date"], format="%Y-%m-%d", errors="coerce").dt.year
    frame["implement_year"] = (
        ex_year.fillna(announce.dt.year)
        .where(~frame["announce_date_suspect"])
        .astype("Int64")
    )

    frame["cash_per_share_pretax"] = (frame["cash_per10_pretax"] / 10).round(6)
    frame["has_cash"] = frame["cash_per10_pretax"].fillna(0) > 0
    frame["has_bonus_share"] = frame["bonus_share_per10"].fillna(0) > 0
    frame["has_transfer_share"] = frame["transfer_share_per10"].fillna(0) > 0

    seq = frame.groupby(frame["announce_date"].fillna("UNKNOWN"), sort=False).cumcount() + 1
    frame["record_id"] = [
        f"{code}-{date or 'UNKNOWN'}#{n}" for date, n in zip(frame["announce_date"].fillna("UNKNOWN"), seq)
    ]

    return frame[DIVIDEND_COLUMNS]


def build_rights_frame(raw_dir: Path, code: str, name: str) -> pd.DataFrame:
    """配股列表页解析（结构与分红表不同，单独处理）。"""
    list_path = raw_dir / f"list_{code}.html"
    if not list_path.exists():
        return pd.DataFrame(columns=RIGHTS_COLUMNS)

    html = list_path.read_text(encoding="utf-8")
    rows = parse_list_rows(html, list_url(code), "sharebonus_2", RIGHTS_LIST_FIELDS)
    if not rows:
        return pd.DataFrame(columns=RIGHTS_COLUMNS)

    records = []
    for row in rows:
        records.append(
            {
                "stock_code": code,
                "stock_name": name,
                "announce_date": row.get("announce_date"),
                **{field: row.get(field) for field in RIGHTS_LIST_FIELDS if field != "announce_date"},
                "source_url": row.get("detail_url") or list_url(code),
            }
        )

    frame = pd.DataFrame(records, columns=RIGHTS_COLUMNS)
    for column in ("stock_code", "stock_name", "source_url"):
        frame[column] = frame[column].map(clean_text)
    for column in RIGHTS_COLUMNS:
        if column in ("stock_code", "stock_name", "source_url", "record_id"):
            continue
        if column in DATE_FIELDS:
            frame[column] = frame[column].map(normalize_date)
        else:
            frame[column] = frame[column].map(to_number)

    seq = frame.groupby(frame["announce_date"].fillna("UNKNOWN"), sort=False).cumcount() + 1
    frame["record_id"] = [
        f"{code}-R{date or 'UNKNOWN'}#{n}"
        for date, n in zip(frame["announce_date"].fillna("UNKNOWN"), seq)
    ]
    return frame[RIGHTS_COLUMNS]


# ---------------------------------------------------------------- 质量校验
CHECK_INDEX = {check["id"]: check for check in CHECKS}


def run_checks(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """逐条执行 10 条质量规则，返回问题清单。"""
    issues: list[dict[str, Any]] = []

    def add(row: pd.Series, rule: str, field: str, message: str) -> None:
        issues.append(
            {
                "stock_code": row.get("stock_code"),
                "record_id": row.get("record_id"),
                "rule": rule,
                "field": field,
                "level": CHECK_INDEX[rule]["level"],
                "message": message,
            }
        )

    def present(value: Any) -> bool:
        return value is not None and not pd.isna(value) and value != ""

    for _, row in frame.iterrows():
        announce = row.get("announce_date")
        ex_date = row.get("ex_dividend_date")
        record_date = row.get("record_date")

        # R1 关键字段完整性
        if not present(row.get("stock_code")):
            add(row, "R1", "stock_code", "股票代码缺失")
        if not present(announce):
            add(row, "R1", "announce_date", "公告日期缺失或无法解析")

        # R2 方案内容有效性
        plan_values = [
            row.get("bonus_share_per10"),
            row.get("transfer_share_per10"),
            row.get("cash_per10_pretax"),
        ]
        positive = [value for value in plan_values if present(value) and value > 0]
        if not positive:
            add(row, "R2", "cash_per10_pretax", "送股 / 转增 / 派息三项均为 0 或缺失，按空方案记录")

        # R3 / R4 日期顺序
        if (
            present(announce)
            and present(ex_date)
            and not bool(row.get("announce_date_suspect"))
            and str(ex_date) < str(announce)
        ):
            add(row, "R3", "ex_dividend_date", f"除权除息日 {ex_date} 早于公告日 {announce}")
        if present(record_date) and present(ex_date) and str(record_date) > str(ex_date):
            add(row, "R4", "record_date", f"股权登记日 {record_date} 晚于除权除息日 {ex_date}")

        # R5 / R6 数值合理性
        for field in NUMERIC_FIELDS:
            value = row.get(field)
            if not present(value):
                continue
            if value < 0:
                add(row, "R5", field, f"{FIELD_LABELS.get(field, field)}为负值：{value}")
            if field in ("bonus_share_per10", "transfer_share_per10", "cash_per10_pretax") \
                    and value > MAX_PER10_VALUE:
                add(row, "R6", field,
                    f"{FIELD_LABELS.get(field, field)}为 {value}，超过合理上界 {MAX_PER10_VALUE:g}")

        # R7 明细页交叉校验
        list_cash = row.get("cash_per10_pretax")
        detail_cash = row.get("detail_cash_pretax")
        if present(list_cash) and present(detail_cash) and abs(list_cash - detail_cash) > DETAIL_TOLERANCE:
            add(row, "R7", "detail_cash_pretax",
                f"列表页派息 {list_cash} 与明细页税前红利 {detail_cash} 差额超过 {DETAIL_TOLERANCE} 元")

        # R9 公告日期合理性（源站占位日期）
        if present(announce) and str(announce) < EARLIEST_REASONABLE_ANNOUNCE_DATE:
            add(row, "R9", "announce_date",
                f"公告日期 {announce} 早于 {EARLIEST_REASONABLE_ANNOUNCE_DATE}，判定为源站占位日期")

        # R10 日期格式可解析
        for field in DATE_FIELDS:
            value = row.get(field)
            if present(value) and not DATE_PATTERN.match(str(value)):
                add(row, "R10", field, f"{FIELD_LABELS.get(field, field)}取值 {value} 不符合 yyyy-mm-dd 格式")

    # R8 主键唯一（同股票 + 同公告日期）
    keyed = frame.copy()
    keyed["_key"] = keyed["announce_date"].fillna(keyed["record_id"])
    duplicated = keyed.duplicated(subset=["stock_code", "_key"], keep=False)
    for _, row in keyed[duplicated].iterrows():
        issues.append(
            {
                "stock_code": row.get("stock_code"),
                "record_id": row.get("record_id"),
                "rule": "R8",
                "field": "announce_date",
                "level": CHECK_INDEX["R8"]["level"],
                "message": f"同一股票公告日期 {row.get('announce_date')} 出现重复记录，清理后保留一条",
            }
        )

    return issues


def drop_duplicates(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """按 (股票代码, 公告日期) 去重，未知日期用记录编号兜底。"""
    keyed = frame.copy()
    keyed["_key"] = keyed["announce_date"].fillna(keyed["record_id"])
    removed = int(keyed.duplicated(subset=["stock_code", "_key"], keep="first").sum())
    keyed = keyed.drop_duplicates(subset=["stock_code", "_key"], keep="first")
    return keyed.drop(columns="_key"), removed


# ---------------------------------------------------------------- 汇总与导出
def build_yearly_frame(dividends: pd.DataFrame) -> pd.DataFrame:
    """按股票 + 分红年度汇总，供趋势图与年度明细使用。"""
    valid = dividends[dividends["dividend_year"].notna()].copy()
    if valid.empty:
        return pd.DataFrame(columns=YEARLY_COLUMNS)
    valid["dividend_year"] = valid["dividend_year"].astype(int)
    grouped = valid.groupby(["stock_code", "stock_name", "dividend_year"], as_index=False).agg(
        records=("record_id", "count"),
        cash_records=("has_cash", "sum"),
        cash_per_share_sum=("cash_per_share_pretax", "sum"),
        bonus_share_per10_sum=("bonus_share_per10", "sum"),
        transfer_share_per10_sum=("transfer_share_per10", "sum"),
    )
    for column in ("cash_per_share_sum", "bonus_share_per10_sum", "transfer_share_per10_sum"):
        grouped[column] = grouped[column].round(4)
    grouped["cash_records"] = grouped["cash_records"].astype(int)
    grouped = grouped.sort_values(["stock_code", "dividend_year"]).reset_index(drop=True)
    return grouped[YEARLY_COLUMNS]


def build_stocks_frame(dividends: pd.DataFrame, rights: pd.DataFrame) -> pd.DataFrame:
    """按目标股票汇总记录数、累计派息与最近一期方案。"""
    rows: list[dict[str, Any]] = []
    for item in TARGET_STOCKS:
        code = item["code"]
        all_records = dividends[dividends["stock_code"] == code]
        valid = all_records[~all_records["announce_date_suspect"].fillna(False)]
        cash_total = float(valid["cash_per_share_pretax"].sum())
        cash_years = int(
            valid[valid["has_cash"]]["dividend_year"].dropna().astype(int).nunique()
        )
        latest_status = None
        if not valid.empty:
            latest_row = valid.sort_values("announce_date").iloc[-1]
            latest_status = latest_row.get("status")
        rows.append(
            {
                "stock_code": code,
                "stock_name": (valid["stock_name"].dropna().iloc[0]
                               if not valid["stock_name"].dropna().empty else code),
                "market": item["market"],
                "industry": item["industry"],
                "dividend_records": int(len(all_records)),
                "rights_records": int(len(rights[rights["stock_code"] == code])),
                "cash_total_pretax": round(cash_total, 4),
                "dividend_years": cash_years,
                "cash_avg_per_year": round(cash_total / cash_years, 4) if cash_years else None,
                "first_announce_date": valid["announce_date"].min() if not valid.empty else None,
                "latest_announce_date": valid["announce_date"].max() if not valid.empty else None,
                "latest_status": latest_status,
            }
        )
    return pd.DataFrame(rows, columns=STOCKS_COLUMNS)


def frame_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame → JSON 可序列化记录（NaN 转为 null）。"""
    if frame.empty:
        return []
    return json.loads(frame.to_json(orient="records", force_ascii=False))


def frame_to_chinese(frame: pd.DataFrame, labels: dict[str, str]) -> pd.DataFrame:
    """导出前把字段名换成中文，布尔值换成是 / 否。"""
    renamed = frame.rename(columns=labels)
    for field in BOOLEAN_FIELDS:
        label = labels.get(field)
        if label in renamed.columns:
            renamed[label] = renamed[label].map({True: "是", False: "否"})
    return renamed


def display_width(text: str) -> int:
    """用于 Excel 列宽估算：中文按 2 个字符宽度计算。"""
    return sum(2 if ord(char) > 127 else 1 for char in text)


def export_excel(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    """导出多 Sheet Excel，并自动调整列宽。"""
    from openpyxl.utils import get_column_letter

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)
            worksheet = writer.sheets[name]
            for index, column in enumerate(frame.columns, start=1):
                sample = [str(value) for value in frame[column].head(400).tolist()]
                width = max([display_width(str(column))] + [display_width(value) for value in sample] or [10])
                worksheet.column_dimensions[get_column_letter(index)].width = min(max(width + 2, 8), 42)


def build_coverage(frame: pd.DataFrame, columns: list[str]) -> dict[str, float]:
    """字段覆盖率：非空值占比。"""
    if frame.empty:
        return {column: 0.0 for column in columns}
    return {column: round(float(frame[column].notna().mean()), 4) for column in columns}


# ---------------------------------------------------------------- 主流程
def run(
    *,
    codes: list[str] | None = None,
    raw_dir: Path = RAW_DIR,
    data_dir: Path = DATA_DIR,
) -> dict[str, Any]:
    data_dir.mkdir(parents=True, exist_ok=True)
    codes = codes or [item["code"] for item in TARGET_STOCKS]

    dividend_frames: list[pd.DataFrame] = []
    rights_frames: list[pd.DataFrame] = []
    for code in codes:
        list_path = raw_dir / f"list_{code}.html"
        if not list_path.exists():
            raise FileNotFoundError(
                f"缺少 {list_path}，请先运行 scripts/fetch_sina.py 抓取原始页面"
            )
        name = parse_stock_name(list_path.read_text(encoding="utf-8"), code)
        dividend_frames.append(build_dividend_frame(raw_dir, code, name))
        rights_frames.append(build_rights_frame(raw_dir, code, name))

    dividends = pd.concat(dividend_frames, ignore_index=True)
    rights = pd.concat(rights_frames, ignore_index=True) if rights_frames else pd.DataFrame(columns=RIGHTS_COLUMNS)

    # 先在去重前跑校验（R8 需要看到重复行），再执行去重
    issues = run_checks(dividends)
    dividends, duplicates_removed = drop_duplicates(dividends)

    yearly = build_yearly_frame(dividends)
    stocks = build_stocks_frame(dividends, rights)
    issues_frame = pd.DataFrame(
        issues, columns=["stock_code", "record_id", "rule", "field", "level", "message"]
    )

    rule_hits = {check["id"]: 0 for check in CHECKS}
    for item in issues:
        rule_hits[item["rule"]] = rule_hits.get(item["rule"], 0) + 1

    level_counts = {"error": 0, "warning": 0, "info": 0}
    for item in issues:
        level_counts[item["level"]] = level_counts.get(item["level"], 0) + 1

    quality_report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "source": SOURCE,
        "targets": TARGET_STOCKS,
        "counts": {
            "stocks": len(stocks),
            "dividend_records": int(len(dividends)),
            "rights_records": int(len(rights)),
            "yearly_rows": int(len(yearly)),
            "issues": len(issues),
            "duplicates_removed": duplicates_removed,
            "detail_pages": len(list(raw_dir.glob("detail_*.html"))),
        },
        "checks": [
            {
                **check,
                "hits": rule_hits.get(check["id"], 0),
                "passed": rule_hits.get(check["id"], 0) == 0,
            }
            for check in CHECKS
        ],
        "issue_summary": level_counts,
        "issue_by_rule": {key: value for key, value in rule_hits.items() if value},
        "field_coverage": build_coverage(dividends, DIVIDEND_COLUMNS),
        "rights_field_coverage": build_coverage(rights, RIGHTS_COLUMNS),
        "field_dictionary": {
            column: {
                "label": FIELD_LABELS.get(column, RIGHTS_LABELS.get(column, column)),
                "description": FIELD_DESCRIPTIONS.get(column, ""),
            }
            for column in DIVIDEND_COLUMNS
        },
        "notes": NOTES,
    }

    # ---- 落盘：CSV 用中文表头（utf-8-sig 便于 Excel 直接打开），JSON 保留英文字段名
    dividends_cn = frame_to_chinese(dividends, FIELD_LABELS)
    rights_cn = frame_to_chinese(rights, RIGHTS_LABELS)
    yearly_cn = frame_to_chinese(yearly, YEARLY_LABELS)
    stocks_cn = frame_to_chinese(stocks, STOCKS_LABELS)
    issues_cn = issues_frame.rename(columns=ISSUES_LABELS)

    dividends_cn.to_csv(data_dir / "dividends.csv", index=False, encoding="utf-8-sig")
    rights_cn.to_csv(data_dir / "rights.csv", index=False, encoding="utf-8-sig")
    yearly_cn.to_csv(data_dir / "yearly.csv", index=False, encoding="utf-8-sig")
    stocks_cn.to_csv(data_dir / "stocks.csv", index=False, encoding="utf-8-sig")
    issues_cn.to_csv(data_dir / "issues.csv", index=False, encoding="utf-8-sig")

    for name, frame in (
        ("dividends", dividends),
        ("rights", rights),
        ("yearly", yearly),
        ("stocks", stocks),
        ("issues", issues_frame),
    ):
        (data_dir / f"{name}.json").write_text(
            json.dumps(frame_records(frame), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    (data_dir / "quality_report.json").write_text(
        json.dumps(quality_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    export_excel(
        data_dir / "dividends.xlsx",
        {
            "分红明细": dividends_cn,
            "配股记录": rights_cn,
            "年度汇总": yearly_cn,
            "股票汇总": stocks_cn,
            "问题清单": issues_cn,
        },
    )

    return quality_report


def main() -> None:
    parser = argparse.ArgumentParser(description="解析并清洗新浪财经历史分红数据")
    parser.add_argument("--codes", nargs="*", help="仅处理指定股票代码")
    args = parser.parse_args()

    report = run(codes=args.codes)
    counts = report["counts"]
    print(
        f"[解析] 股票 {counts['stocks']} 只，分红记录 {counts['dividend_records']} 条，"
        f"配股记录 {counts['rights_records']} 条，年度汇总 {counts['yearly_rows']} 行"
    )
    print(
        f"[质量] 问题 {counts['issues']} 条（错误 {report['issue_summary']['error']} / "
        f"提示 {report['issue_summary']['warning']} / 信息 {report['issue_summary']['info']}），"
        f"清理重复 {counts['duplicates_removed']} 条"
    )
    for check in report["checks"]:
        flag = "通过" if check["passed"] else f"命中 {check['hits']}"
        print(f"  {check['id']} {check['name']}：{flag}")
    print(f"[输出] {DATA_DIR}")


if __name__ == "__main__":
    main()
