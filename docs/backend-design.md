# Moola 后端设计方案（为 prototype 原型配套）

> 目标：给 `prototype/index.html`（简约记账高保真前端原型）配套一个真实可用的后端，
> 把前端里的假数据（`app.js` 的 `INITIAL_TX`）替换为从数据库实时拉取，并支持记账、统计、日历、搜索等全部交互。

---

## 1. 现状盘点

### 1.1 前端原型（prototype/）需要什么

前端 `app.js` 的核心数据模型：

```js
// 分类
TYPES = {
  expense: [{ name: '餐饮', icon: 'cate_restaurant.png' }, ...14个],
  income:  [{ name: '工资', icon: 'cate_salary.png' }, ...8个],
}

// 账单（按日期分组）
INITIAL_TX = [
  { date: '2026-08-02', items: [
      { type: '餐饮', remark: '瑞幸咖啡 · 拿铁', money: -19.90 },  // money<0 支出 / >0 收入
  ]},
  ...
]
```

前端需要的页面能力：明细列表、本月概览、记账（计算器+类型网格）、统计（周/月/年柱状图+环形图）、日历（每日标记）、搜索、分类管理、账本管理、设置、经济简讯、会员。

前端目前**无任何 fetch 调用**，全部是内存假数据。

### 1.2 现有后端（app/）已有什么

| 模块 | 能力 | 复用度 |
|------|------|--------|
| `app/db.py` | SQLite 连接 + 建表（ledgers / categories / transactions / budgets / feed_sources） | ✅ 直接复用 |
| `app/models.py` | `add_transaction` / `add_many` / `list_transactions` / `list_categories` / `add_category` / `set_budget` / `add_source` / `list_sources` | ✅ 大部分复用 |
| `app/parser/wechat_csv.py` | 微信账单 CSV 解析 | ✅ 复用 |
| `app/analyzer/report.py` | 月度报告（总额/分类占比/daily/异常/预算预警） | ✅ 复用 |
| `app/analyzer/classify.py` | AI 自动分类 | ✅ 复用 |
| `app/web/app.py` | Flask：`GET /`、`GET /api/transactions`、`GET /api/report`、`POST /api/transactions` | ⚠️ 需扩展 |

**缺口**：统计/日历/搜索/账本/设置/导出 等接口、账单的更新/删除、跨域支持、原型静态托管。

---

## 2. 架构与技术栈

```
┌─────────────────────────────┐
│  prototype/index.html       │  前端原型（复用 glory 已做好的 UI/交互）
│  （Flask 托管 or 独立 8088）│
└──────────────┬──────────────┘
               │  fetch /api/*
┌──────────────▼──────────────┐
│  Flask 后端 (port 5001)     │  app/web/ + app/api/ 蓝图
│  路由 → models → SQLite     │
└──────────────┬──────────────┘
               ▼
        data/moola.db (SQLite)
```

**技术栈建议（保持轻量，不引入重框架）**：
- Flask（已有）+ SQLite（已有，`sqlite3` 标准库即可，无需 SQLAlchemy）
- `flask-cors`：仅在前后端分离（8088 + 5001）时需要；若 Flask 直接托管原型则不需要
- 图表：前端已用原生 canvas 自绘，后端只需给聚合数据
- AI 分类：复用 `app/analyzer/classify.py`（可对接 LLM API）

### 部署方案（二选一）

- **方案 A（推荐，简单）**：Flask 同时托管原型静态文件 + API，单端口 5001，无跨域。
  做法：`app = Flask(__name__, static_folder='../../prototype', static_url_path='')`，或把 `prototype/` 拷入 `app/web/static/prototype/`。
- **方案 B（前后端分离）**：原型继续跑 8088，API 在 5001，Flask 加 `flask-cors`。适合后续前端独立部署。

---

## 3. 数据模型

现有表已够用，**无需改表结构**，仅需**新增一张设置表**（可选）。

### 3.1 数据格式映射（前端 ↔ 后端）

前端条目 → 后端 transactions 行：

| 前端字段 | 后端字段 | 转换 |
|----------|----------|------|
| `date` | `trans_time` | `trans_time[:10]` |
| `type` | `category` | 直接映射 |
| `remark` | `merchant` + `note` | `remark.split(' · ')`，第一段→merchant，其余→note |
| `money` | `amount` | 直接映射（负=支出，正=收入） |

后端返回给前端时按此反向映射，前端**几乎不用改**。

### 3.2 建议新增表（可选）

```sql
-- 用户设置（MVP 单用户，存 key-value）
CREATE TABLE IF NOT EXISTS user_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- 分类图标（可并入 categories 表加 icon 列，或前端自带映射）
ALTER TABLE categories ADD COLUMN icon TEXT DEFAULT '';
```

---

## 4. API 接口设计（完整清单）

> 前缀统一 `/api`，返回 JSON。金额 `amount`：负=支出，正=收入。时间 `trans_time`：`YYYY-MM-DD HH:MM:SS`。

### 4.1 账单 CRUD（明细页 / 记账页）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/transactions?month=YYYY-MM&limit=&category=` | 查询账单（`trans_time` 倒序） |
| GET | `/api/transactions/group?month=YYYY-MM` | **按日期分组**，直接喂给明细页：`{summary:{expense,income,balance}, groups:[{date,spend,income,items:[{type,remark,money}]}]}` |
| GET | `/api/transactions/<id>` | 单条 |
| POST | `/api/transactions` | 新增 `{amount, category, merchant, note, trans_time}` |
| PUT | `/api/transactions/<id>` | 修改 |
| DELETE | `/api/transactions/<id>` | 删除 |

### 4.2 统计（统计页）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats/trend?period=week\|month\|year&cat=expense\|income&end=YYYY-MM-DD` | 柱状图数据：`{buckets:[{label,value}], max}` |
| GET | `/api/stats/category?period=month&month=YYYY-MM&cat=expense` | 环形图占比：`[{name,value}]`（按分类聚合） |

> 现有 `analyzer/report.py` 已产出 `by_category` 与 `daily`，可直接复用做月/年；周、年需新增聚合函数（建议在 `app/analyzer/stats.py`）。

### 4.3 日历（日历页）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/calendar?month=YYYY-MM` | `{days:[{date, expense, income, count}]}`，前端据此画绿点/选中态 |

### 4.4 搜索（搜索页）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/search?q=&mode=bill\|category&sort=time\|amount&order=desc\|asc` | 账单内搜索（q 匹配 merchant/note/category），或按分类聚合。`LIKE %q%` 即可 |

### 4.5 分类（记账页 / 类别管理页）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/categories?kind=expense\|income` | 分类列表（含 icon） |
| POST | `/api/categories` | 新增 `{name, kind, icon}` |
| PUT | `/api/categories/<id>` | 改名/改图标 |
| DELETE | `/api/categories/<id>` | 删除（有账单引用时前端提示改账单） |

### 4.6 账本（账本管理页）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/books` | 账本列表（含默认） |
| POST | `/api/books` | 新建 `{name, type}` |
| PUT | `/api/books/<id>` | 编辑名称/类型 |
| DELETE | `/api/books/<id>` | 删除 |
| POST | `/api/books/<id>/merge` | 合并到另一账本 |

### 4.7 设置（我的页）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/settings` | 返回全部设置 |
| PUT | `/api/settings` | 保存 `{bigDisplay, moneyColor, sort, startDay, ...}` |

> MVP 也可直接用浏览器 `localStorage`，后端设置接口作为可选。

### 4.8 导入导出 / AI 分类（命令行已有，补 HTTP）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/import/wechat` | 上传微信 CSV（multipart），复用 `wechat_csv.py` |
| GET | `/api/export.csv?month=` | 导出 CSV（`csv` 模块） |
| POST | `/api/classify?month=` | 对未分类记录跑 AI 分类 |

### 4.9 经济简讯（feed，Phase 4）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/feeds` | 订阅源列表 |
| POST | `/api/feeds` | 新增订阅源 |
| GET | `/api/feeds/articles` | 拉取聚合文章（RSS 解析或静态示例） |

---

## 5. 鉴权与多设备

- **MVP（单用户本地）**：不做登录，直接访问。
- **多设备/公网**：加简单 API Token（`X-API-Key` header），Flask 装饰器校验；预留 `users` 表。
- **部署**：开发用 Flask dev server 即可；生产用 `waitress` / `gunicorn`。

---

## 6. 实施计划（分 4 个 Phase）

### Phase 1 — 数据打通（最重要）
- [ ] `models.py` 补：`get_transaction` / `update_transaction` / `delete_transaction` / `search_transactions` / 分组查询
- [ ] `app/api/` 蓝图：`transactions`（含 `/group`）+ CORS/静态托管（方案 A 或 B）
- [ ] 前端：把 `INITIAL_TX` 改为 `fetch('/api/transactions/group?month=' + 当前月)`；记账完成调 `POST /api/transactions`
- [ ] 验证：明细页显示真实数据、FAB 记账能写入库

### Phase 2 — 统计 + 日历
- [ ] `app/analyzer/stats.py`：trend（week/month/year）+ category 聚合
- [ ] `/api/stats/*`、`/api/calendar` 接口
- [ ] 前端统计页/日历页接真实数据

### Phase 3 — 搜索 + 分类 + 账本
- [ ] `/api/search`、`/api/categories`（增删改）、`/api/books`
- [ ] 前端搜索页、类别管理页、账本管理页接入

### Phase 4 — 导入导出 + AI + 简讯
- [ ] 微信 CSV 上传/导出、AI 分类按钮
- [ ] 经济简讯订阅源
- [ ] （可选）部署与备份

---

## 7. 需要新增/修改的后端文件

```
app/
├── db.py                        # ✅ 不变（可加 user_settings 表）
├── models.py                    # ✏️ 补 update/delete/search/group/books/settings
├── analyzer/
│   ├── report.py                # ✅ 复用
│   ├── stats.py                 # ➕ 新增（trend/category 聚合）
│   └── classify.py              # ✅ 复用
└── web/
    ├── app.py                   # ✏️ 注册蓝图 / CORS / 静态托管
    └── api/                     # ➕ 新增蓝图目录
        ├── __init__.py
        ├── transactions.py
        ├── stats.py
        ├── calendar.py
        ├── search.py
        ├── categories.py
        ├── books.py
        ├── settings.py
        └── feeds.py
docs/backend-design.md           # 📄 本文档
```

---

## 8. 关键决策点（供确认）

1. **部署方案**：A（Flask 托管原型，单端口 5001，推荐）还是 B（分离 + CORS）？
2. **统计周期粒度**：周/月/年 都做，还是先做月？
3. **设置存储**：后端 `user_settings` 表 还是前端 `localStorage`？
4. **AI 分类**：接哪个 LLM（需 API Key）还是先规则分类？
5. **会员/云备份/指纹**：原型里有这些页面，MVP 先做占位（页面存在、后端空实现）？
