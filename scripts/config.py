"""项目级配置：数据源、目标股票、字段口径与管线说明。

本文件是整条数据管线的唯一事实来源：抓取、清洗、校验、建站脚本都从这里
读取配置，避免同一口径散落在多个脚本里。
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SITE_DIR = PROJECT_ROOT / "site"
ASSETS_DIR = SITE_DIR / "assets"
DOCS_DIR = PROJECT_ROOT / "docs"

# ---------------------------------------------------------------- 数据源
SOURCE = {
    "name": "新浪财经",
    "home": "https://finance.sina.com.cn/",
    "list_url": (
        "http://vip.stock.finance.sina.com.cn/corp/go.php/"
        "vISSUE_ShareBonus/stockid/{code}.phtml"
    ),
    "detail_url": (
        "http://vip.stock.finance.sina.com.cn/corp/view/"
        "vISSUE_ShareBonusDetail.php"
    ),
    "referer": "http://vip.stock.finance.sina.com.cn/",
    "encoding": "gb2312",
    "license": "数据版权归新浪财经及原始披露方所有，本项目仅用于课程学习与研究演示。",
}

# ---------------------------------------------------------------- 目标股票
# 5 只股票覆盖白酒、家电、银行、保险四类行业，兼有「高分红」与「含配股」形态
TARGET_STOCKS = [
    {"code": "600519", "market": "上交所主板", "industry": "白酒"},
    {"code": "000858", "market": "深交所主板", "industry": "白酒"},
    {"code": "000333", "market": "深交所主板", "industry": "家用电器"},
    {"code": "600036", "market": "上交所主板", "industry": "股份制银行"},
    {"code": "601318", "market": "上交所主板", "industry": "保险"},
]

# ---------------------------------------------------------------- 抓取参数
FETCH = {
    "delay_seconds": 0.8,      # 请求间隔，礼貌抓取
    "timeout": 25,
    "retries": 3,
    "user_agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
}

# 清洗阶段视为缺失值的占位符
NULL_TOKENS = {
    "", "-", "--", "---", "—", "――", "暂无", "暂无数据", "不适用",
    "null", "None", "NaN", "无",
}

# ---------------------------------------------------------------- 字段口径
DIVIDEND_COLUMNS = [
    "stock_code", "stock_name", "record_id", "announce_date", "announce_date_suspect",
    "dividend_year", "allocation_type", "implement_year", "status",
    "bonus_share_per10", "transfer_share_per10", "cash_per10_pretax",
    "cash_per_share_pretax", "ex_dividend_date", "record_date", "bonus_listing_date",
    "detail_cash_pretax", "detail_cash_aftertax", "shareholders_meeting_date",
    "dividend_pay_date", "has_cash", "has_bonus_share", "has_transfer_share",
    "source_url",
]

RIGHTS_COLUMNS = [
    "stock_code", "stock_name", "record_id", "announce_date", "rights_per10",
    "rights_price", "base_share_capital", "ex_rights_date", "record_date",
    "payment_start", "payment_end", "listing_date", "raised_funds", "source_url",
]

YEARLY_COLUMNS = [
    "stock_code", "stock_name", "dividend_year", "records", "cash_records",
    "cash_per_share_sum", "bonus_share_per10_sum", "transfer_share_per10_sum",
]

STOCKS_COLUMNS = [
    "stock_code", "stock_name", "market", "industry", "dividend_records",
    "rights_records", "cash_total_pretax", "dividend_years", "cash_avg_per_year",
    "first_announce_date", "latest_announce_date", "latest_status",
]

FIELD_LABELS: dict[str, str] = {
    "stock_code": "股票代码",
    "stock_name": "股票名称",
    "record_id": "记录编号",
    "announce_date": "公告日期",
    "announce_date_suspect": "公告日期存疑",
    "dividend_year": "分红年度",
    "allocation_type": "分配类型",
    "implement_year": "实施年度",
    "status": "方案进度",
    "bonus_share_per10": "送股(股/10股)",
    "transfer_share_per10": "转增(股/10股)",
    "cash_per10_pretax": "派息税前(元/10股)",
    "cash_per_share_pretax": "每股派息税前(元)",
    "ex_dividend_date": "除权除息日",
    "record_date": "股权登记日",
    "bonus_listing_date": "红股上市日",
    "detail_cash_pretax": "明细页税前红利(元)",
    "detail_cash_aftertax": "明细页税后红利(元)",
    "shareholders_meeting_date": "股东大会决议公告日",
    "dividend_pay_date": "红利到账日",
    "has_cash": "含现金分红",
    "has_bonus_share": "含送股",
    "has_transfer_share": "含转增",
    "source_url": "数据来源",
}

RIGHTS_LABELS: dict[str, str] = {
    "stock_code": "股票代码",
    "stock_name": "股票名称",
    "record_id": "记录编号",
    "announce_date": "公告日期",
    "rights_per10": "配股方案(股/10股)",
    "rights_price": "配股价格(元)",
    "base_share_capital": "基准股本(股)",
    "ex_rights_date": "除权日",
    "record_date": "股权登记日",
    "payment_start": "缴款起始日",
    "payment_end": "缴款终止日",
    "listing_date": "配股上市日",
    "raised_funds": "募集资金合计(元)",
    "source_url": "数据来源",
}

YEARLY_LABELS: dict[str, str] = {
    "stock_code": "股票代码",
    "stock_name": "股票名称",
    "dividend_year": "分红年度",
    "records": "记录数",
    "cash_records": "含现金分红记录数",
    "cash_per_share_sum": "每股派息合计(元)",
    "bonus_share_per10_sum": "送股合计(股/10股)",
    "transfer_share_per10_sum": "转增合计(股/10股)",
}

STOCKS_LABELS: dict[str, str] = {
    "stock_code": "股票代码",
    "stock_name": "股票名称",
    "market": "上市板块",
    "industry": "行业",
    "dividend_records": "分红记录数",
    "rights_records": "配股记录数",
    "cash_total_pretax": "累计每股派息税前(元)",
    "dividend_years": "含现金分红年度数",
    "cash_avg_per_year": "年均每股派息(元)",
    "first_announce_date": "最早公告日期",
    "latest_announce_date": "最近公告日期",
    "latest_status": "最近方案进度",
}

ISSUES_LABELS: dict[str, str] = {
    "stock_code": "股票代码",
    "record_id": "记录编号",
    "rule": "规则",
    "field": "字段",
    "level": "级别",
    "message": "说明",
}

FIELD_DESCRIPTIONS: dict[str, str] = {
    "stock_code": "6 位证券代码，来源于项目目标清单",
    "stock_name": "证券简称，从数据源页面解析",
    "record_id": "派生字段：记录主键，格式 {股票代码}-{公告日期}#序号",
    "announce_date": "分红方案公告日期，统一为 ISO 格式 yyyy-mm-dd；源站未知日期以 1900-01-01 占位",
    "announce_date_suspect": "派生字段：公告日期早于 1990-01-01 时标记为 True，该行不参与年度派生与区间统计",
    "dividend_year": "派生字段：按公告月份推断的利润归属年度（公告月份不超过 8 月归上一自然年度）",
    "allocation_type": "派生字段：年度分配 / 中期分配，按公告月份推断，仅用于分组统计",
    "implement_year": "派生字段：除权除息日所在年份，缺失时回退到公告年份",
    "status": "数据源给出的方案进度，如「实施」",
    "bonus_share_per10": "每 10 股送股数，缺失按 0 处理",
    "transfer_share_per10": "每 10 股转增数，缺失按 0 处理",
    "cash_per10_pretax": "每 10 股税前派息金额（元）",
    "cash_per_share_pretax": "派生字段：每 10 股税前派息 ÷ 10",
    "ex_dividend_date": "除权除息日",
    "record_date": "股权登记日",
    "bonus_listing_date": "红股上市日，未送股时为缺失",
    "detail_cash_pretax": "分红明细页给出的税前红利，用于与列表页交叉校验",
    "detail_cash_aftertax": "分红明细页给出的税后红利",
    "shareholders_meeting_date": "股东大会决议公告日，来自明细页",
    "dividend_pay_date": "红利 / 送转股到账日，来自明细页",
    "has_cash": "派生字段：本次方案是否包含现金分红",
    "has_bonus_share": "派生字段：本次方案是否包含送股",
    "has_transfer_share": "派生字段：本次方案是否包含转增",
    "source_url": "该条记录对应的数据源页面地址",
}

# ---------------------------------------------------------------- 管线说明
# 展示页「实现过程」一节直接读取该结构，保证文档与页面一致
PIPELINE_STEPS = [
    {
        "id": "plan",
        "title": "需求确认（Plan 模式）",
        "summary": "先用 Plan 模式把目标、范围、字段口径、交付物和验收标准确认清楚，再动手实现。",
        "points": [
            "明确数据源与抓取范围：5 只股票、列表页 + 明细页",
            "明确清洗口径：占位符归零、日期标准化、派生字段规则",
            "明确交付物：数据集、展示页、测试报告、对话记录",
        ],
        "evidence": ["docs/01-需求确认单.md"],
    },
    {
        "id": "fetch",
        "title": "原始数据抓取",
        "summary": "列表页与明细页全量存档到本地，请求限速 + 失败重试，并记录抓取清单。",
        "points": [
            "会话复用 + 0.8 秒请求间隔，尊重数据源",
            "失败请求指数退避重试，最多 3 次",
            "manifest 记录每条请求的 URL、字节数、SHA-256 与耗时",
        ],
        "evidence": ["scripts/fetch_sina.py", "data/raw/manifest.json"],
    },
    {
        "id": "clean",
        "title": "解析与清洗",
        "summary": "从 HTML 表格抽取记录，占位符归一为缺失，类型转换，并合并明细页字段。",
        "points": [
            "解析 sharebonus_1 / sharebonus_2 / sharebonusdetail 三张表",
            "日期标准化为 ISO 格式，数值字段转为浮点数",
            "明细页字段并入记录，供交叉校验使用",
        ],
        "evidence": ["scripts/preprocess.py"],
    },
    {
        "id": "validate",
        "title": "派生与质量校验",
        "summary": "生成年度与股票汇总，执行 10 条质量规则，输出问题清单与质量报告。",
        "points": [
            "派生记录编号、分红年度、每股派息、是否含现金/送股/转增",
            "10 条规则覆盖完整性、有效性、顺序、数值范围与跨页一致性",
            "问题按信息 / 提示 / 错误分级，全部可追溯到记录",
        ],
        "evidence": ["data/quality_report.json", "data/issues.csv"],
    },
    {
        "id": "publish",
        "title": "可视化与端到端测试",
        "summary": "把结果打包成零网络依赖的静态站点，并用 Playwright 完成功能、布局与截图测试。",
        "points": [
            "站点数据内嵌为 data.js，双击 index.html 即可离线查看",
            "Playwright 覆盖功能、布局、无障碍与截图三大类用例",
            "测试报告与截图随仓库一起交付",
        ],
        "evidence": ["site/index.html", "tests/", "docs/screenshots/"],
    },
]
