# Moola (FinSight) 后端实现蓝图 + 施工计划

> 借鉴来源：小遥账单（Flask 分层/动态表头/18 分析函数）、actual-ai（LLM 限流/批量/fallback）、EasyAccounts（二级分类/AI 即 MCP/报表推送）、skx6（CSV 解析坑）
> 对齐战略：《战略分析-个人财富管家项目.md》Phase 0-4；数据模型：`docs/db-schema.md`（v2 务实版）
> 核心原则：**务实优先**——MVP 只做能"自己用起来"的最小闭环，复杂能力按阶段演进。

---

## 1. 技术栈与总体架构

```
┌────────────────────────────────────────────────┐
│  前端原型 prototype/index.html（glory 已做好）  │
└──────────────────────┬─────────────────────────┘
                       │ fetch /api/*
┌──────────────────────▼─────────────────────────┐
│  Flask (Python 3.14)  —— app/web/app.py        │
│  ├─ 静态托管原型（方案 A：单端口 5001，无 CORS）│
│  └─ 注册 API 蓝图                              │
└──────────────────────┬─────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────┐
│  app/services/（业务逻辑层，从开源项目借鉴）    │
│  importer → classifier → analyzer → profile    │
│       → recommender → digester                 │
└──────────────────────┬─────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────┐
│  app/models/（数据访问层） + app/db.py         │
│  SQLite：data/moola.db（v2 schema：6 核心表）  │
└────────────────────────────────────────────────┘
```

**技术选型**：
- **Flask**（已有）+ **SQLite/sqlite3**（已有）——个人应用零运维
- **pandas**：CSV 解析与聚合（小遥验证可行，处理编码/废行/¥ 清理最顺手）
- **feedparser**：RSS 解析（Phase 3 简讯用）
- **APScheduler**：定时任务（分类批量 / 订阅源抓取 / 每日快照）——借鉴 actual-ai 的 cron 模式
- **requests + 模型 API**：分类与 AI 分析（DeepSeek 等，可换）

---

## 2. 从开源项目借鉴的核心要点

| 来源 | 借鉴点 | 落点 |
|------|--------|------|
| **小遥账单** | ① `parser/services/api` 三层分层 ② **动态找表头**（不硬编码行号）③ `utf-8-sig`/GBK 编码处理 ④ ¥ 清理、退款/关闭/撤销取负 ⑤ 18 个分析函数 | `services/importer.py`、`services/analyzer.py` |
| **actual-ai** | ① **LLM 模型工厂 + fallback**（多 provider 切换）② **双维度限流**（requests/min + tokens/min）③ **cron 批量定时分类** ④ 严格错误分类（限流 vs 一般）⑤ **JSON 输出容错解析** | `services/classifier.py` |
| **EasyAccounts** | ① 二级分类 ② **AI 即 MCP**（SSE，任何 MCP 客户端可查账，加分项）③ Excel/邮件报表推送兜底 ④ **AI 角色 prompt 文件**（约束 AI 行为） | 分类、`services/analyzer.py`、`ai/prompts/` |
| **skx6** | ① 微信=UTF-8/前16行废行/11列；支付宝=GBK/前4行/16列 ② 列名数值去空格、去 ¥ | `services/importer.py` 兼容性矩阵 |

---

## 3. 后端模块设计（目录结构）

```
moola/
├── main.py                     # CLI 入口（init/import/classify/report/web）
├── config.yaml                 # 分类规则、LLM 配置、抓取配置
├── app/
│   ├── db.py                   # SQLite 连接 + SCHEMA（v2：6 核心表）
│   ├── models/                 # 数据访问层（每域一个文件）
│   │   ├── __init__.py
│   │   ├── transactions.py     # 账单 CRUD + 分组 + 搜索 + 聚合
│   │   ├── categories.py       # 分类 CRUD
│   │   ├── rules.py            # 分类规则 CRUD + 命中计数
│   │   ├── budgets.py          # 预算
│   │   ├── interests.py        # 画像标签
│   │   └── reports.py          # AI 分析报告存档
│   ├── services/               # 业务逻辑层（核心）
│   │   ├── __init__.py
│   │   ├── importer.py         # 微信/支付宝 CSV 导入（动态表头/编码/退款）
│   │   ├── classifier.py       # AI 分类引擎（规则→LLM、限流、批量、学习）
│   │   ├── analyzer.py         # 统计/分析（借鉴小遥 18 函数，按需裁剪）
│   │   ├── profile.py          # 用户画像推导（流水→标签+权重）
│   │   ├── recommender.py      # 推荐打分（画像×文章 topics）
│   │   └── digester.py         # 简讯组装（daily/weekly）
│   ├── feeds/                  # RSS/文章抓取（Phase 3）
│   │   ├── fetcher.py
│   │   └── topics.py           # AI 提取文章主题标签
│   ├── ai/                     # LLM 封装
│   │   ├── llm.py              # 模型工厂 + fallback + 限流 + JSON 容错
│   │   └── prompts/            # 角色 prompt 文件（分类/分析/推荐理由）
│   ├── api/                    # Flask 蓝图（每个资源一个）
│   │   ├── __init__.py         # 注册所有蓝图
│   │   ├── _util.py            # 前后端字段映射 + 统一响应
│   │   ├── transactions.py     # GET/POST/PUT/DELETE + /group
│   │   ├── stats.py            # 趋势/分类占比
│   │   ├── calendar.py         # 每日聚合
│   │   ├── search.py
│   │   ├── categories.py
│   │   ├── import_export.py    # 上传 CSV / 导出 CSV
│   │   ├── classify.py         # 触发分类
│   │   ├── profile.py          # 画像展示
│   │   ├── reports.py          # AI 分析报告
│   │   ├── feeds.py            # 订阅源/文章/推荐/简讯
│   │   └── settings.py
│   └── web/
│       ├── app.py              # create_app()：静态托管 + 注册蓝图
│       ├── templates/          # 占位（或直接托管 prototype/）
│       └── static/
└── data/                       # moola.db + uploads/
```

---

## 4. API 设计（完整清单）

> 前缀 `/api`，返回 JSON；金额 `amount` 负=支出、正=收入；时间 `trans_time` 为 `YYYY-MM-DD HH:MM:SS`。

### 4.1 账单
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/transactions?month=&category=&limit=` | 列表（倒序） |
| GET | `/api/transactions/group?month=` | **按日期分组**（喂给前端明细页，含 summary） |
| GET | `/api/transactions/<id>` | 单条 |
| POST | `/api/transactions` | 新增 `{amount, category, merchant, note, trans_time, source}` |
| PUT | `/api/transactions/<id>` | 修改 |
| DELETE | `/api/transactions/<id>` | 删除 |

### 4.2 统计 / 日历
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats/trend?period=week\|month\|year&cat=expense\|income` | 柱状图数据 |
| GET | `/api/stats/category?month=&cat=` | 环形图分类占比 |
| GET | `/api/calendar?month=` | `{days:[{date,expense,income,count}]}` |

### 4.3 搜索
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/search?q=&mode=bill\|category&sort=time\|amount&order=` | LIKE 搜索 |

### 4.4 分类 / 导入导出 / 分类
| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST/PUT/DELETE | `/api/categories` | 分类 CRUD（含 icon） |
| POST | `/api/import/wechat` `/api/import/alipay` | multipart 上传，返回 {新增, 跳过} |
| GET | `/api/export.csv?month=` | 导出 |
| POST | `/api/classify?month=` | 对未分类记录跑分类引擎 |

### 4.5 画像 / 报告 / 简讯（Phase 2-3）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/profile` | 用户画像标签 + 权重 |
| GET/POST | `/api/reports` | AI 分析报告列表/生成（`analysis_reports`） |
| GET | `/api/feeds` + `/api/feeds/articles` | 订阅源与文章 |
| GET | `/api/digests` | 生成的简讯 |

---

## 5. 核心实现要点（含开源借鉴的技术细节）

### 5.1 导入器 `services/importer.py` —— 小遥方案

```python
def _find_header_row(lines, keywords=('交易时间', '交易创建时间')):
    for i, line in enumerate(lines):
        if all(k in line for k in keywords):
            return i
    raise ValueError('未找到表头')

def parse_wechat(path):
    raw = path.read_bytes()
    text = raw.decode('utf-8-sig', errors='replace')   # 微信 UTF-8 带 BOM
    header = _find_header_row(text.splitlines())
    # pandas 读取 → 清理 ¥/逗号 → 退款/关闭/撤销 金额取负 → 派生 月份/日期/来源='wechat'

def parse_alipay(path):
    text = path.read_text(encoding='gbk', errors='replace')  # 支付宝 GBK
    # 跳过前 4 行废行，动态找表头，16 列映射
```

要点：
- **动态找表头**（不硬编码行号），兼容各版本
- 编码探测：先 `utf-8-sig`，失败再 GBK
- **退款/关闭/撤销**状态 → `amount` 取负
- 去重：`dedup_key = md5(trans_time|amount|merchant)`

### 5.2 分类引擎 `services/classifier.py` —— actual-ai 模式

```python
class Classifier:
    def classify_batch(self, month):            # cron/手动批量
        pending = models.transactions.unclassified(month)
        for tx in pending:
            cat = self._rule_classify(tx)       # ① 本地规则（零成本）
            if not cat:
                cat = self._llm_classify(tx)    # ② LLM（限流保护）
            self._apply(tx, cat)
            if user_corrected: rules.bump(tx, cat)  # ③ 学习：命中计数++
```

- **模型工厂 + fallback**：主 provider（DeepSeek）失败 → 备用
- **双维度限流**：`requests/min` + `tokens/min`，放 `config.yaml` 可调
- **JSON 容错解析**：LLM 返回 `{"category": "..."}`，剥离代码块/多余字符
- **错误分类**：429/限流 → 标记稍后重试；其他 → 保留未分类
- 命中计数 → 规则权重 → "越用越准"

### 5.3 分析引擎 `services/analyzer.py` —— 小遥 18 函数裁剪

| 阶段 | 函数 | 服务 |
|------|------|------|
| P0/P1 | 月度总额/分类占比/daily/异常/预算 | 报告 + 明细页 |
| P2 | 趋势（周/月/年）、日历聚合 | 统计页/日历页 |
| P2 | 拿铁因子、夜间消费、周末 vs 周一 | 洞察型分析 |
| P4 | 订阅检测、恩格尔系数、品牌忠诚、桑基图 | AI 报告素材 |

### 5.4 画像推导 `services/profile.py`

```
读取 transactions → 按规则表（config.yaml）计算维度 → 输出 (tag, weight)
写入 user_interests(source='from_finance')
示例：月均房租→'租房族'；瑞幸频次≥5→'咖啡控'；工资固定入账→'工薪族'
```

### 5.5 推荐 `services/recommender.py` + 简讯 `digester.py`

```
score = Σ(interest.weight × topic_match(article.topics)) × freshness × (1 - read_bias)
digester 按日/周组装 digests，附 reason（AI 生成推荐理由，合规话术）
```

---

## 6. 施工计划（对齐战略，务实推进）

### Phase 0 收尾（当前，2026.8-9）—— 自己用起来
| # | 任务 | 借鉴 |
|---|------|------|
| 1 | 重建 v2 数据库（6 表）+ 迁移示例数据 | - |
| 2 | `importer.py`：微信+支付宝解析（动态表头/编码/退款） | 小遥+skx6 |
| 3 | `classifier.py`：规则→LLM、规则持久化、命中计数 | actual-ai |
| 4 | `config.yaml` 扩充关键词规则库 | - |
| 5 | `main.py` 命令对接（import/classify/report） | - |
| 6 | **导入真实账单，自用 + 分类准确率≥90% 抽查** | - |

### Phase 1（2026.9-11）—— 原型接通（周留存≥25%）
| # | 任务 |
|---|------|
| 1 | `api/` 蓝图骨架 + `_util.py` 字段映射 |
| 2 | `/api/transactions`（含 group）+ 前端明细页/记账接入 |
| 3 | `/api/stats/*` + `/api/calendar` + 前端统计/日历 |
| 4 | `/api/search` + 前端搜索页 |
| 5 | 多账本 + 自定义分类（Phase 1 战略要求） |

### Phase 2（2026.11-2027.2）—— 付费点（转化≥3%）
| # | 任务 |
|---|------|
| 1 | 预算管理 + 超支预警（budgets 表） |
| 2 | 存款目标（AI 算每月存多少） |
| 3 | AI 月度报告（故事化）→ analysis_reports 存档 |
| 4 | 对话式查询（"上月吃饭花了多少"） |
| 5 | Pro 订阅边界（付费解锁 AI 深度报告/无限分类/多账本） |

### Phase 3（2027.2-6）—— 差异化（NAS≥100 付费 / 推送活跃≥40%）
| # | 任务 |
|---|------|
| 1 | `feeds/` 抓取器 + 文章 topics 提取（feedparser + AI） |
| 2 | 画像推导 profile.py 落地 |
| 3 | 推荐 + 简讯 digester（**守合规：只推通用知识，附免责声明**） |
| 4 | NAS 部署版评估（本地模型跑分类/分析） |

---

## 7. 工程纪律

- **成本控制**：分类/分析全部走 `ai/llm.py`（限流+批量+fallback），单条几分钱封顶
- **口径统一**：`_util.py` 做前后端字段映射，金额正负、时间格式单一来源
- **可回滚**：改库前备份 `data/moola.db.bak`
- **月度复盘**：每月一份《月度使用报告》（真实数据，也是对外素材）
- **合规自检**：对外展示过合规自检；AI 建议附"仅供参考，不构成投资建议"

---

## 8. 一句话总结

> 后端 = **小遥的干净分层 + actual-ai 的省钱 AI 分类 + EasyAccounts 的功能启发 + 我们的画像/推送闭环**。Phase 0 先把"导入→分类→报告"跑通并自己用起来，再逐阶段接通原型、付费、推送。
