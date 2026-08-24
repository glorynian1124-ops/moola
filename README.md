# Moola · 个人财务健康 AI 助手

> 从记账开始，用 AI 完成「记录 → 分析 → 规划 → 推送」闭环的个人财务健康管家。
> 数据本地可控（SQLite），合规克制（不荐股、不代客理财）。

Moola 是集 **自动记账、多账本、数据统计、AI 数据分析、AI 对话分析、个性化经济简讯** 于一体的个人财务健康助手：

- 从微信/支付宝导出 CSV，一键导入并 **AI 自动分类**
- **多账本**管理（新建/编辑/删除/切换，前后端打通）
- 月度/年度消费分析、趋势、消费结构图、异常提醒
- **「经济分析」AI 聊天**：消费结构分析、消费者画像、存钱建议，支持「直连 DeepSeek / 平台托管」双接入
- 基于消费行为的 **用户画像** 与 **健康评分**
- 类 Feedly 的 **个性化经济简讯推送**（开源差异化空白点）

## ✨ 核心能力

| 能力 | 说明 |
|------|------|
| 🧾 自动记账 | 微信/支付宝 CSV 一键导入（自动识别来源、动态表头、退款处理）；AI 自动分类（本地规则优先 → 大模型兜底），命中即学习、越用越准 |
| 📒 多账本 | 前端账本管理（新建/编辑/删除/切换，长按进入管理模式）+ 后端 `ledgers` 表；所有查询按 `ledger_id` 隔离 |
| 📊 数据统计 | 统计页三栏：趋势柱状图（消费/收入趋势）、消费结构环形图、明细列表；月度/年度报告、日历视图、全文搜索 |
| 🤖 AI 经济分析 | 底部「经济分析」AI 聊天页：消费结构分析、消费者画像、存钱建议等；**双接入**——① 直连 DeepSeek（用户自填 Key）② 平台托管（管理员分配 Key，预留 VIP/计费） |
| 🔑 AI 服务配置 | 「我的」页入口 + 配置覆盖页：接入模式 / API Key / 平台地址，Key 随时更换；后端 `ai_keys` 表存 Key（列表脱敏，管理平台可读写） |
| 📬 个性化简讯 | 按用户画像 × 文章主题匹配，Feedly 模式推送（只推通用知识，不涉及具体标的） |

## 🛠️ 技术栈

- 后端：Python 3 + Flask + SQLite
- 解析：csv / 编码探测（微信 UTF-8、支付宝 GBK、动态表头）
- AI：DeepSeek（OpenAI 兼容接口，规则优先 + 每日限流控制成本；前端可直连或经后端代理）
- 前端：原生 HTML/CSS/JS 高保真原型（`prototype/`，交互完整可操作，CSS mask 白色图标上色体系）

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库（建表 + 导入默认分类规则）
python main.py init

# 3. 导入微信 / 支付宝账单（auto 自动识别来源，支持 CSV 与微信 Excel）
python main.py import 微信账单.csv
python main.py import --source alipay 支付宝账单.csv
python main.py import 微信支付账单流水文件(...).xlsx   # 微信官方 Excel 账单同样支持

# 4. AI 自动分类（规则优先，未命中再调大模型，每日限流）
python main.py classify 2026-07

# 5. 月度消费报告
python main.py report 2026-07

# 6. 启动本地 Web（手机连同一 WiFi 可访问）
python main.py web
```

### 前端原型（prototype/）

- **两种打开方式**：① 直接浏览器打开 `prototype/index.html`（纯静态）；② 后端运行后访问 `http://127.0.0.1:5001`（接通真实数据库）
- **5 个 Tab**：明细 / 统计 / 经济分析 / 经济简讯 / 我的
- **经济分析（AI 聊天）**：首次使用到「我的 → AI 服务配置」填 DeepSeek API Key（存本机 `localStorage`，可随时更换）；请求优先走后端代理 `POST /api/ai/chat`，未实现时自动直连 DeepSeek
- **多账本**：明细页顶部可新建/切换账本，数据按账本隔离

> 💡 **协作者 / 新机器初始化**：clone 后只需
> `pip install -r requirements.txt` + `python main.py init`，即可得到完整数据库框架
> （10+ 张表 + 默认账本 + 默认分类 + 分类规则），随后 `python main.py import 你的账单.xlsx`
> 填充自己的数据即可使用。数据库结构也可单独查看 `schema.sql`。
>
> 🔐 **隐私**：`data/moola.db`（个人账单 + `ai_keys` 表）已在 `.gitignore` 中排除，**不会上传**。
> - AI 自动分类 Key：用环境变量 `MOOLA_API_KEY` 配置，**勿把真实 Key 写入 `config.yaml` 并提交**（该文件被 Git 跟踪，公开仓库会泄露）
> - 前端 AI Key：存浏览器 `localStorage`，不入代码；后端 `ai_keys` 表存本地 SQLite，列表接口脱敏，管理平台可读写

更多命令见 `python main.py -h`（`init` / `import` / `classify` / `rules` / `report` / `web`）。

## 📁 目录结构

```
├── main.py              CLI 入口（init/import/classify/rules/report/web）
├── schema.sql           数据库结构（纯建表 SQL，不含任何数据）
├── config.yaml          配置（LLM、分类规则、预算、服务器）
├── app/
│   ├── db.py            SQLite 连接 + 建表（含 ledgers / ai_keys 等 10+ 张表）
│   ├── models.py        数据访问层（交易 CRUD/分组/搜索、分类规则、画像、报告、AI Key）
│   ├── parser/          账单解析器（wechat_csv.py / wechat_xlsx.py / alipay_csv.py）
│   ├── analyzer/        分析引擎（report.py 月度报告 / classify.py AI 分类）
│   └── web/             Flask Web 服务（API：ledgers / ai-keys / transactions / search…）
├── prototype/           高保真前端原型（简约记账 APK 复刻 + AI 经济分析聊天）
│   ├── index.html       5 Tab 主页面 + 覆盖页（记账/统计/账本/AI 配置…）
│   ├── app.js           核心交互（账本管理/统计/AI 配置与聊天/搜索/日历）
│   ├── api.js           前端 ↔ 后端适配层（bookAPI 账本、aiAPI 双通道 AI）
│   └── assets/          图标（白色 PNG + CSS mask 上色机制）
├── apk_analysis/        APK 逆向分析脚本与产物
├── docs/                设计与规划文档
└── data/                本地数据库与示例数据（个人账单不上传，已 gitignore）
```

## 🗺️ 路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| **Phase 0** | 数据层 v2 + 微信/支付宝导入 + AI 分类引擎 + 月度报告 | ✅ 完成 |
| **Phase 1** | 前端接通真实数据：明细/记账/统计/日历/搜索 + 多账本管理 + AI 经济分析聊天 + AI 服务配置 | ✅ 主体完成（后端 `/api/ai/chat` 代理接口待实现） |
| **Phase 2** | 预算/存款目标/AI 报告/对话查询（付费点：平台托管计费） | 待开始 |
| **Phase 3** | 个性化简讯推送 + NAS 私有化部署（差异化） | 待开始 |

## 📚 设计文档

| 文档 | 内容 |
|------|------|
| `docs/db-schema.md` | 数据库设计（v2 务实版：流水→分类→画像→推荐闭环） |
| `docs/backend-implementation.md` | 后端实现蓝图 + 施工计划（借鉴开源项目） |
| `docs/execution-plan.md` | 执行计划（对齐战略路线图 Phase 0-4） |
| `docs/backend-design.md` | API 接口设计（完整清单） |

## ⚠️ 合规声明

本工具仅提供个人记账、消费分析与通用财务健康知识，**不构成任何投资建议，不涉及具体投资标的推荐**，不做代客理财。

## 📄 License

MIT
