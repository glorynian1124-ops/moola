# Moola 数据库设计 v2（务实版）

> 约束前提：**数据来源只有微信、支付宝交易 CSV**。因此：
> - 不做资产/负债账户体系（无余额数据）
> - 不做多账本/多用户（单机个人应用）
> - 聚焦一条主线：**流水 → 分类 → 画像 → 分析 → 个性化简讯**
>
> 核心思路：**用户画像不靠用户填写，靠 AI 从交易流水推导**。

---

## 1. 设计原则

1. **一张核心表**：`transactions` 承载所有数据，`source` 字段区分微信/支付宝
2. **规则与分类分离**：`category_rules` 让自动分类可学习
3. **画像 = 推导标签**：`user_interests` 存 AI 从流水推导的兴趣标签
4. **AI 有记忆**：`analysis_reports` 存档每次分析，可回溯对比
5. **简讯 = 画像 × 文章**：`user_interests` 匹配 `feed_articles.topics` 生成推荐

```
transactions(流水) ──► categories(分类) ──► category_rules(自动分类+AI学习)
     │                                            │
     ▼                                            ▼
analysis_reports(分析存档) ◄── 画像推导 ──► user_interests(兴趣标签)
                                                   │
                                                   ▼
feed_sources → feed_articles ── 匹配 topics ──► feed_recommendations → digests(简讯)
                                                   ▲
                                        feed_actions(阅读反馈)
```

---

## 2. 核心表（P1 就建，共 6 张）

### 2.1 transactions — 交易流水（唯一数据源）

```sql
CREATE TABLE transactions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    amount     REAL NOT NULL,            -- 负=支出 正=收入
    category   TEXT,                     -- 分类名（冗余存储，查询快）
    merchant   TEXT,                     -- 交易对方/商户
    note       TEXT DEFAULT '',
    trans_time TEXT,                     -- YYYY-MM-DD HH:MM:SS
    source     TEXT NOT NULL DEFAULT 'manual', -- wechat | alipay | manual（来源即"账户"）
    raw_data   TEXT,                     -- 原始 CSV 行（去重审计 + AI 学习）
    dedup_key  TEXT UNIQUE,              -- md5(时间+金额+商户)
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX idx_tx_time   ON transactions(trans_time);
CREATE INDEX idx_tx_cat    ON transactions(category);
CREATE INDEX idx_tx_merchant ON transactions(merchant);
```
> `source` 就是轻量"账户"：微信一个来源、支付宝一个来源，天然分组，无需 accounts 表。

### 2.2 categories — 分类字典

```sql
CREATE TABLE categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,           -- 餐饮/交通/购物...
    kind TEXT NOT NULL DEFAULT 'expense',-- expense | income
    icon TEXT DEFAULT ''
);
```

### 2.3 category_rules — 自动分类规则（AI 学习引擎）

```sql
CREATE TABLE category_rules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword    TEXT,                     -- 关键词（命中即归类）
    category   TEXT NOT NULL,
    source     TEXT NOT NULL DEFAULT 'user', -- user | ai | import
    confidence REAL NOT NULL DEFAULT 1.0,    -- AI 置信度
    hit_count  INTEGER NOT NULL DEFAULT 0,   -- 命中次数=学习权重
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
```
> 来源三路：用户手设 / AI 学习（用户纠正后自动生成）/ 导入模板。
> 命中越多权重越高 → "越用越准"。这是"自动记账"的引擎。

### 2.4 budgets — 预算

```sql
CREATE TABLE budgets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    category     TEXT NOT NULL,
    month        TEXT,                   -- YYYY-MM；NULL=滚动
    limit_amount REAL NOT NULL,
    UNIQUE(category, month)
);
```

### 2.5 user_interests — 用户画像标签 ⭐

```sql
CREATE TABLE user_interests (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tag        TEXT NOT NULL,                    -- 兴趣/特征标签
    weight     REAL NOT NULL DEFAULT 1.0,        -- 权重（信号越强越高）
    source     TEXT NOT NULL DEFAULT 'from_finance', -- from_finance | from_reads | explicit
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE(tag, source)
);
```

### 2.6 analysis_reports — AI 分析存档

```sql
CREATE TABLE analysis_reports (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    period       TEXT,                   -- YYYY-MM
    kind         TEXT,                   -- monthly | health_score | insight
    summary      TEXT,                   -- AI 摘要（自然语言）
    insights     TEXT,                   -- JSON 洞察列表
    health_score REAL,                   -- 收支健康分 0-100
    metrics      TEXT,                   -- JSON 指标快照（结余率/固定支出占比等）
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
```

---

## 3. 用户画像推导方案（核心价值）

> 所有推导只依赖 `transactions`。规则可放 `config.yaml`，也可由 AI 动态生成。

### 3.1 推导维度与示例规则

| 画像维度 | 推导逻辑 | 产出标签 (tag) | 置信信号 |
|---------|---------|---------------|---------|
| 生活状态 | 每月固定大额支出（房租/月供） | `租房族` `有车族` `养宠族` | 连续 ≥3 个月同商户同金额 |
| 消费结构 | 分类占比 TOP1-2 | `餐饮重度` `购物达人` | 占比 >40% |
| 消费水平 | 月均支出 / 单笔均值 | `高消费` `精打细算` | 分位数对比 |
| 通勤方式 | 交通明细 | `地铁通勤` `打车族` | 频次统计 |
| 外卖偏好 | 美团/饿了么频次 | `外卖重度` | 月 ≥10 次 |
| 咖啡/奶茶 | 瑞幸/星巴克/蜜雪频次 | `咖啡控` `奶茶控` | 月 ≥5 次 |
| 健身 | 健身房月卡 | `健身爱好者` | 同商户周期扣款 |
| 数码/时尚 | 京东/苹果/品牌店 | `数码爱好者` `潮人` | 金额+频次 |
| 旅行 | 机票/酒店/携程 | `旅行爱好者` | 年度频次 |
| 收入特征 | 工资/转账入账规律 | `工薪族` `自由职业` | 固定日期+稳定金额 |
| 消费时间 | 工作日/周末/夜间分布 | `夜猫子` `周末宅` | 交易时间分布 |

### 3.2 推导流程

```
每月（或每次分析时）：
  1. 读取 transactions
  2. 按规则计算各维度 → 得到候选标签 + 权重
  3. 写入 user_interests（source='from_finance'），权重取最大信号
  4. 生成健康分与洞察 → 存入 analysis_reports
```

### 3.3 画像 → 个性化简讯链路

```
user_interests(from_finance)  ──┐
user_interests(from_reads)   ──┼──► 匹配 feed_articles.topics
user_interests(explicit)     ──┘        │
                                        ▼
                          feed_recommendations(打分+理由)
                                        ▼
                                   digests(简讯)
```

举例：画像有 `租房族`+`咖啡控` → 简讯推送"租房省钱技巧"+"咖啡平替测评"，附理由"根据你每月 ¥2,000 房租与 ¥300 咖啡消费"。

---

## 4. 个性化简讯表（P4 建，共 5 张）

```sql
-- 订阅源
CREATE TABLE feed_sources (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    url            TEXT NOT NULL UNIQUE,
    category       TEXT DEFAULT '',     -- 财经|科技|房产|消费...
    enabled        INTEGER NOT NULL DEFAULT 1,
    last_fetched   TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 文章（topics 为 AI 提取的主题标签，用于匹配画像）
CREATE TABLE feed_articles (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id  INTEGER NOT NULL REFERENCES feed_sources(id),
    title      TEXT NOT NULL,
    link       TEXT UNIQUE,
    summary    TEXT,
    content    TEXT,
    published  TEXT,
    topics     TEXT DEFAULT '[]',       -- JSON ["租房","省钱",...]
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 阅读行为（隐式兴趣信号）
CREATE TABLE feed_actions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL REFERENCES feed_articles(id),
    action     TEXT NOT NULL,           -- read|bookmark|like|hide
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE(article_id, action)
);

-- 推荐打分
CREATE TABLE feed_recommendations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL REFERENCES feed_articles(id),
    score      REAL NOT NULL,
    reason     TEXT,                    -- 推荐理由（给用户看）
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 组装好的简讯
CREATE TABLE digests (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    period     TEXT,                    -- daily|weekly
    title      TEXT,
    content    TEXT,                    -- JSON 文章块
    reason     TEXT,
    status     TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
```

---

## 5. 迁移与落地

- 现有库仅 14 条测试数据 → **直接重建**（备份为 `moola.db.bak`）
- `app/db.py` 更新 SCHEMA；`app/models.py` 适配新字段（去 account_id 等）
- `wechat_csv.py` 补 `source='wechat'`，新增支付宝 CSV 解析 `alipay_csv.py`
- 重新导入示例数据验证

| 阶段 | 建表 |
|------|------|
| P1 | transactions / categories / category_rules / budgets |
| P2 | user_interests / analysis_reports（画像+分析） |
| P4 | feed 系列 5 张 |

---

## 6. 一句话总结

> **一张流水表 + 一套推导规则 = 完整用户画像**；画像再驱动分析与简讯。复杂账户体系让位给"微信/支付宝两个 source"——用最少的表，把数据变成洞察。
