from __future__ import annotations

import json
import math
import statistics
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path.home() / "Downloads" / "比亚迪后复权历史行情数据.xlsx"
OUTPUT = ROOT / "src" / "data" / "byd.json"

HEADERS = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
    "振幅": "amplitude",
    "涨跌幅": "changePercent",
    "涨跌额": "change",
    "换手率": "turnoverRate",
}


def percentage(value: float) -> float:
    return round(value * 100, 2)


def max_drawdown(rows: list[dict]) -> dict:
    peak_value = -math.inf
    peak_date = ""
    max_drawdown_value = 0.0
    max_peak_date = ""
    trough_date = ""

    for row in rows:
        close = row["close"]
        if close > peak_value:
            peak_value = close
            peak_date = row["date"]
        drawdown = close / peak_value - 1
        if drawdown < max_drawdown_value:
            max_drawdown_value = drawdown
            max_peak_date = peak_date
            trough_date = row["date"]

    return {
        "value": percentage(max_drawdown_value),
        "peakDate": max_peak_date,
        "troughDate": trough_date,
    }


def monthly_returns(rows: list[dict]) -> list[dict]:
    month_last_close: OrderedDict[str, float] = OrderedDict()
    for row in rows:
        month_last_close[row["date"][:7]] = row["close"]

    result = []
    previous_close = rows[0]["close"]
    for month, close in month_last_close.items():
        result.append(
            {
                "month": month,
                "label": f"{int(month[5:7])}月",
                "return": percentage(close / previous_close - 1),
            }
        )
        previous_close = close
    return result


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Source workbook not found: {SOURCE.name}")

    workbook = openpyxl.load_workbook(SOURCE, data_only=True, read_only=True)
    sheet = workbook["Sheet2"]
    raw_rows = list(sheet.iter_rows(values_only=True))
    header = raw_rows[0]
    field_map = [HEADERS[name] for name in header]

    rows = []
    for raw in raw_rows[1:]:
        if not raw or raw[0] is None:
            continue
        item = {}
        for field, value in zip(field_map, raw):
            if field == "date":
                if isinstance(value, datetime):
                    item[field] = value.strftime("%Y-%m-%d")
                else:
                    item[field] = str(value)[:10]
            else:
                item[field] = float(value)
        rows.append(item)

    rows.sort(key=lambda item: item["date"])
    closes = [row["close"] for row in rows]
    daily_returns = [
        closes[index] / closes[index - 1] - 1 for index in range(1, len(closes))
    ]
    best_day = max(rows, key=lambda item: item["changePercent"])
    worst_day = min(rows, key=lambda item: item["changePercent"])
    high_row = max(rows, key=lambda item: item["high"])
    low_row = min(rows, key=lambda item: item["low"])
    drawdown = max_drawdown(rows)

    summary = {
        "company": "比亚迪",
        "ticker": "002594.SZ",
        "priceBasis": "后复权",
        "startDate": rows[0]["date"],
        "endDate": rows[-1]["date"],
        "tradingDays": len(rows),
        "firstClose": rows[0]["close"],
        "lastClose": rows[-1]["close"],
        "lastChange": rows[-1]["change"],
        "lastChangePercent": rows[-1]["changePercent"],
        "periodReturn": percentage(closes[-1] / closes[0] - 1),
        "high": high_row["high"],
        "highDate": high_row["date"],
        "low": low_row["low"],
        "lowDate": low_row["date"],
        "maxDrawdown": drawdown["value"],
        "drawdownPeakDate": drawdown["peakDate"],
        "drawdownTroughDate": drawdown["troughDate"],
        "annualizedVolatility": percentage(
            statistics.stdev(daily_returns) * math.sqrt(252)
        ),
        "upDays": sum(1 for row in rows if row["changePercent"] > 0),
        "downDays": sum(1 for row in rows if row["changePercent"] < 0),
        "flatDays": sum(1 for row in rows if row["changePercent"] == 0),
        "bestDay": {
            "date": best_day["date"],
            "value": best_day["changePercent"],
        },
        "worstDay": {
            "date": worst_day["date"],
            "value": worst_day["changePercent"],
        },
        "totalAmount": sum(row["amount"] for row in rows),
        "averageTurnoverRate": round(
            statistics.mean(row["turnoverRate"] for row in rows), 2
        ),
    }

    payload = {
        "meta": {
            "sourceName": SOURCE.name,
            "sheet": "Sheet2",
            "generatedAt": "2026-10-18",
            "note": "Historical adjusted prices. Not a live quote or investment advice.",
        },
        "summary": summary,
        "monthlyReturns": monthly_returns(rows),
        "rows": rows,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {len(rows)} rows to {OUTPUT.relative_to(ROOT)} "
        f"({summary['startDate']} to {summary['endDate']})."
    )


if __name__ == "__main__":
    main()

