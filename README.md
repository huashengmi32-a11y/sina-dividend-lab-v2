# 新浪财经历史分红数据获取与预处理（基于 Codex）

课程作业第三章实践项目：把新浪财经个股页面上的历史分红数据抓取下来，
清洗成结构化数据集，并用一个零网络依赖的静态页面展示**实现过程、数据结果、
质量报告与网页测试结论**。

- 展示页：`site/index.html`（双击即可离线打开）
- 在线预览：<https://huashengmi32-a11y.github.io/sina-dividend-lab-v2/>
- 仓库地址：<https://github.com/huashengmi32-a11y/sina-dividend-lab-v2>
- 数据集：`data/`（CSV / JSON / Excel / 质量报告）
- 测试：`tests/`（Playwright，功能 + 布局 + 无障碍 + 截图）
- 文档：`docs/`（需求确认单、UI 设计说明、测试报告、Agent 对话记录）

## 一、项目做了什么

| 环节 | 产物 | 说明 |
|------|------|------|
| 需求确认 | `docs/01-需求确认单.md` | Plan 模式下确认数据源、股票范围、字段口径、交付物与验收标准 |
| 数据抓取 | `data/raw/`、`data/raw/manifest.json` | 列表页 + 明细页全量存档；限速 0.8 秒、失败退避重试；每条请求记录 URL、字节数、SHA-256 与耗时 |
| 解析清洗 | `data/*.csv`、`data/*.json`、`data/dividends.xlsx` | 三张源表解析、占位符归一、日期标准化、派生 8 个分析字段 |
| 质量校验 | `data/quality_report.json`、`data/issues.csv` | 10 条规则逐条打标，问题分错误 / 提示 / 信息三级 |
| 可视化 | `site/` | 指标卡、数据表（搜索 + 分页）、三张 SVG 图表、字段字典、测试与截图墙 |
| 测试验收 | `tests/report/index.html`、`docs/screenshots/` | 桌面 + 移动视口的功能、布局、无障碍与截图用例 |

## 二、快速开始

```bash
# 1. 安装依赖
python -m pip install -r requirements.txt
npm install

# 2. 抓取原始页面（结果带缓存，重复执行不会重复请求）
python scripts/fetch_sina.py

# 3. 清洗、校验并导出数据集
python scripts/preprocess.py

# 4. 跑测试 → 报告脱敏 → 打包展示页数据（顺序固定，报告要先于打包生成）
npx playwright test
python scripts/sanitize_report.py
python scripts/build_site.py
```

可选脚本：

```bash
python scripts/fetch_fonts.py     # 重新下载自托管字体（Poppins / Open Sans latin 子集）
npm run report                   # 打开 Playwright HTML 报告
npm run serve                    # 以项目根目录启动静态服务（默认 4185 端口）
```

## 三、目录结构

```
sina-dividend-lab-v2/
├─ scripts/
│  ├─ config.py           # 数据源、目标股票、字段口径、管线说明（唯一事实来源）
│  ├─ sina_common.py      # 列表页 / 明细页地址与缓存命名规则
│  ├─ fetch_sina.py       # 抓取：缓存 + 限速 + 重试 + 抓取清单
│  ├─ preprocess.py       # 解析、清洗、派生、10 条质量校验、多格式导出
│  ├─ build_site.py       # 生成 site/assets/data.js，收集截图与测试结果
│  ├─ sanitize_report.py  # 提交前把测试报告里的本机绝对路径替换为占位符
│  └─ fetch_fonts.py      # 下载并自托管展示页字体
├─ data/                  # 数据集与质量报告（raw/ 为可重新生成的抓取缓存）
├─ site/                  # 展示页面（index.html + assets/）
├─ tests/                 # Playwright 用例与报告
├─ design-system/         # ui-ux-pro-max 生成的设计系统
└─ docs/                  # 需求确认单、设计说明、测试报告、对话记录、截图
```

## 四、数据快照（2026-09-27 抓取）

| 指标 | 数值 |
|------|------|
| 目标股票 | 5 只（贵州茅台、五粮液、美的集团、招商银行、中国平安） |
| 存档页面 | 154 个（列表页 5 + 明细页 149） |
| 分红记录 | 146 条 |
| 配股记录 | 3 条 |
| 年度汇总 | 110 行 |
| 字段 | 24 个（含 8 个派生字段） |
| 质量规则 | 10 条，命中 17 条提示（0 错误） |
| 累计每股派息（税前） | 贵州茅台 325.66 元、五粮液 39.27 元、中国平安 26.78 元、美的集团 26.41 元、招商银行 19.85 元 |

## 五、数据来源与合规

- 数据源：新浪财经个股「分红送转」页与「分红明细」页；
- 抓取方式：公开页面、低频访问（0.8 秒间隔）、携带常规浏览器 UA；
- 版权说明：数据版权归新浪财经及原始披露方所有，本项目仅用于课程学习与研究演示；
- 派生字段（分红年度、分配类型等）为统计推断，不代表公司官方口径。

## 六、展示页说明

页面所有数字均由脚本产物生成（`scripts/build_site.py` → `site/assets/data.js`），
不发起任何外部请求，可离线打开。设计系统来自 `ui-ux-pro-max` 技能，
详见 `docs/02-UI设计说明.md`。

## 七、测试说明

```bash
npx playwright test              # 全部用例（桌面 + 移动）
npx playwright test --project=desktop-chromium
npx playwright test --project=mobile-chromium
```

- 功能用例：`tests/site.spec.js`（页面数值与 `data/` 产物交叉校验、搜索分页、图表、零外部请求、无控制台错误）；
- 布局用例：`tests/layout.spec.js`（375 / 768 / 1024 / 1440 四视口的横向滚动、文字溢出、触控尺寸、锚点遮挡、对比度）；
- 截图用例：`tests/screenshots.spec.js`（桌面 7 张 + 移动 3 张，输出到 `docs/screenshots/`）。

注意：Windows 环境下默认复用系统自带 Microsoft Edge（`channel: msedge`），
避免下载 Playwright 自带浏览器；如需自带 Chromium，先执行 `npx playwright install chromium`
并设置环境变量 `PW_CHANNEL=bundled`。
