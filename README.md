# Moola · 个人财务健康 AI 助手

> 从记账开始，用 AI 完成「记录 → 分析 → 规划 → 推送」闭环的个人财务健康管家。
> 数据本地可控（SQLite），合规克制（不荐股、不代客理财）。

Moola 是集 **自动记账、数据统计、AI 数据分析、个性化经济简讯** 于一体的个人财务健康助手：

- 从微信/支付宝导出 CSV，一键导入并 **AI 自动分类**
- 月度/年度消费分析、趋势、异常提醒
- 基于消费行为的 **用户画像** 与 **健康评分**
- 类 Feedly 的 **个性化经济简讯推送**（开源差异化空白点）

## ✨ 核心能力

| 能力 | 说明 |
|------|------|
| 🧾 自动记账 | 微信/支付宝 CSV 一键导入（自动识别来源、动态表头、退款处理）；AI 自动分类（本地规则优先 → 大模型兜底），命中即学习、越用越准 |
| 📊 数据统计 | 月度报告、消费结构、趋势柱状图、环形图、日历视图、异常提醒 |
| 🤖 AI 分析 | 用户画像推导（从消费行为读人）、收支健康分、AI 月度报告（故事化）、对话式查询 |
| 📬 个性化简讯 | 按用户画像 × 文章主题匹配，Feedly 模式推送（只推通用知识，不涉及具体标的） |

## 🛠️ 技术栈

- 后端：Python 3 + Flask + SQLite
- 解析：csv / 编码探测（微信 UTF-8、支付宝 GBK、动态表头）
- AI：DeepSeek（OpenAI 兼容接口，规则优先 + 每日限流控制成本）
- 前端：原生 HTML/CSS/JS 高保真原型（`prototype/`，交互完整可操作）

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

更多命令见 `python main.py -h`（`init` / `import` / `classify` / `rules` / `report` / `web`）。

## 📁 目录结构

```
├── main.py              CLI 入口（init/import/classify/rules/report/web）
├── config.yaml          配置（LLM、分类规则、预算、服务器）
├── app/
│   ├── db.py            SQLite 连接 + 建表（v2 schema：6 核心表）
│   ├── models.py        数据访问层（交易 CRUD/分组/搜索、分类规则、画像、报告）
│   ├── parser/          账单解析器（wechat_csv.py / wechat_xlsx.py / alipay_csv.py）
│   ├── analyzer/        分析引擎（report.py 月度报告 / classify.py AI 分类）
│   └── web/             Flask Web 服务（可托管前端原型 + API）
├── prototype/           高保真前端原型（简约记账 APK 复刻，交互完整可操作）
├── apk_analysis/        APK 逆向分析脚本与产物
├── docs/                设计与规划文档
└── data/                本地数据库与示例数据（个人账单不上传，已 gitignore）
```

## 🗺️ 路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| **Phase 0** | 数据层 v2 + 微信/支付宝导入 + AI 分类引擎 + 月度报告 | ✅ 完成 |
| **Phase 1** | 原型前端接通真实数据（明细/记账/统计/日历/搜索/多账本） | ⏳ 进行中 |
| **Phase 2** | 预算/存款目标/AI 报告/对话查询（付费点） | 待开始 |
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
