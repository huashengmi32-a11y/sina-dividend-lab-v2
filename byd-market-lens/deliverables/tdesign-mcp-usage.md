# TDesign MCP 使用记录

## 服务信息

- MCP 名称：`tdesign`
- 包名：`tdesign-mcp-server`
- 版本：`0.2.4`
- Codex 状态：`enabled`
- 传输方式：stdio
- 启动命令：`npx -y tdesign-mcp-server`
- 官方说明：https://cnb.cool/tencent/tdesign/tdesign-mcp-server

Codex 全局配置：

```toml
[mcp_servers.tdesign]
command = "npx"
args = ["-y", "tdesign-mcp-server"]
```

## 可复现调用

```powershell
npm run verify:mcp
```

脚本：`scripts/verify-tdesign-mcp.mjs`

原始结果：`deliverables/tdesign-mcp-report.json`

## 实际调用的工具

| 工具 | 用途 |
| --- | --- |
| `get-component-list` | 获取 `mobile-vue` 组件目录 |
| `get-component-docs` | 查询控件属性与事件 |
| `get-component-dom` | 查询控件真实 DOM 结构 |
| `search-icon` | 查询图表相关 TDesign 图标名称 |
| `get-component-changelog` | 服务提供的版本变更查询能力，已确认可用 |

## 页面使用的控件

| TDesign 控件 | 页面用途 |
| --- | --- |
| `Button` | 数据口径入口、完整交易日展开 |
| `Segmented` | 时间范围、K 线/收盘视图切换 |
| `Switch` | MA5/MA20/MA60 均线显示开关 |
| `Tag` | 全年区间收益状态 |
| `Dialog` | 数据与计算口径说明 |
| `Cell` | 最近 8 个交易日明细 |

## 从 MCP 结果确认的关键 API

- `Segmented` 支持 `options`、`value`、`v-model` 和 `change`。
- `Switch` 支持 `v-model`、`size`、`label` 和 `change`。
- `Tag` 支持 `theme`、`variant`、`size`、`shape`。
- `Dialog` 支持 `visible`、`title`、`confirmBtn`、`cancelBtn`、
  `closeOnOverlayClick` 及关闭事件。
- `Cell` 支持 `title`、`description`、`note`、`bordered`。
- `Button` 支持 `theme`、`variant`、`shape`、`size` 和点击事件。

## 图标查询结果

使用关键词 `chart`、`trend` 调用 `search-icon`，返回的可用图标包括：

```text
chart, chart-3d, chart-add, chart-bar, chart-pie, flowchart,
chart-area, chart-line, chart-ring, play-chart, chart-combo, chart-radar
```

页面图表区域使用 ECharts 绘制；TDesign 图标查询结果用于确认图表语义图标资源。

