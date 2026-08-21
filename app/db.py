"""SQLite 数据库层：初始化 + 连接 + 建表。"""
import os
import sqlite3
from pathlib import Path

# 项目根目录（app/ 的上一级）
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "moola.db"

SCHEMA = """
-- 账本（多账本：name/type/icon 与前端账本卡片一致）
CREATE TABLE IF NOT EXISTS ledgers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT '默认账本',
    type TEXT NOT NULL DEFAULT '标准账本',
    icon TEXT NOT NULL DEFAULT 'ic_accounts.png',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 消费类型（餐饮/交通/购物…，可自定义）
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL DEFAULT 'expense',   -- expense | income
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 账单流水
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ledger_id INTEGER NOT NULL DEFAULT 1 REFERENCES ledgers(id),
    amount REAL NOT NULL,                   -- 正=收入，负=支出
    category TEXT,                          -- 分类名（冗余存储，便于查询）
    merchant TEXT,                          -- 商户名/交易对方
    note TEXT DEFAULT '',                   -- 备注
    trans_time TEXT,                        -- 交易时间 ISO 格式
    source TEXT DEFAULT 'manual',           -- csv_wechat | csv_alipay | screenshot | manual
    raw_data TEXT,                          -- 原始 CSV 行（去重审计 + AI 学习）
    dedup_key TEXT UNIQUE,                  -- 去重键：md5(时间+金额+商户)，多源导入防重复
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_trans_time ON transactions(trans_time);
CREATE INDEX IF NOT EXISTS idx_trans_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_trans_merchant ON transactions(merchant);

-- 预算（分类 × 月份 → 限额）
CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    month TEXT NOT NULL,                    -- 'YYYY-MM'
    limit_amount REAL NOT NULL,
    UNIQUE(category, month)
);

-- 自动分类规则（AI 学习引擎：用户手设 / AI 学习 / 导入模板）
CREATE TABLE IF NOT EXISTS category_rules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword    TEXT,                        -- 关键词（命中即归类）
    category   TEXT NOT NULL,
    source     TEXT NOT NULL DEFAULT 'user', -- user | ai | import
    confidence REAL NOT NULL DEFAULT 1.0,    -- AI 置信度
    hit_count  INTEGER NOT NULL DEFAULT 0,   -- 命中次数 = 学习权重
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_rules_category ON category_rules(category);

-- 用户画像标签（AI 从交易流水推导 + 显式）
CREATE TABLE IF NOT EXISTS user_interests (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tag        TEXT NOT NULL,                    -- 兴趣/特征标签
    weight     REAL NOT NULL DEFAULT 1.0,        -- 权重（信号越强越高）
    source     TEXT NOT NULL DEFAULT 'from_finance', -- from_finance | from_reads | explicit
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE(tag, source)
);

-- AI 分析报告存档（可回溯、可对比）
CREATE TABLE IF NOT EXISTS analysis_reports (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    period       TEXT,                   -- YYYY-MM
    kind         TEXT,                   -- monthly | health_score | insight
    summary      TEXT,                   -- AI 摘要（自然语言）
    insights     TEXT,                   -- JSON 洞察列表
    health_score REAL,                   -- 收支健康分 0-100
    metrics      TEXT,                   -- JSON 指标快照（结余率/固定支出占比等）
    created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- AI 服务 Key（管理平台可查看/分配/修改；本地数据库保存，不入 git）
CREATE TABLE IF NOT EXISTS ai_keys (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,                      -- 名称/用途
    provider   TEXT NOT NULL DEFAULT 'deepseek',   -- deepseek | openai | platform
    base_url   TEXT NOT NULL DEFAULT 'https://api.deepseek.com/v1',
    model      TEXT NOT NULL DEFAULT 'deepseek-v4-flash',
    api_key    TEXT NOT NULL,                      -- 密钥（明文存本地库）
    scope      TEXT NOT NULL DEFAULT 'user',       -- system=自有主Key | user=分发给终端用户
    user_ref   TEXT DEFAULT '',                    -- 平台托管：关联用户标识
    status     INTEGER NOT NULL DEFAULT 1,         -- 1 启用 0 停用
    quota      REAL NOT NULL DEFAULT 0,            -- 剩余额度/次数（0=不限）
    note       TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 订阅源（Feedly 模式，Phase 4）
CREATE TABLE IF NOT EXISTS feed_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,               -- RSS/网页地址
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 文章（订阅源抓取结果）
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER REFERENCES feed_sources(id),
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    summary TEXT DEFAULT '',
    read INTEGER NOT NULL DEFAULT 0,
    starred INTEGER NOT NULL DEFAULT 0,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
"""


def get_conn() -> sqlite3.Connection:
    """获取数据库连接（每次新建，线程安全简单化）。"""
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """建表 + 迁移旧库 + 写入默认账本和默认分类。"""
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        _migrate(conn)
        _seed_ledger(conn)
        _seed_categories(conn)
        conn.commit()
    finally:
        conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    """轻量迁移：为旧库 ledgers 表补齐 type / icon 列。"""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(ledgers)").fetchall()}
    if "type" not in cols:
        conn.execute(
            "ALTER TABLE ledgers ADD COLUMN type TEXT NOT NULL DEFAULT '标准账本'"
        )
    if "icon" not in cols:
        conn.execute(
            "ALTER TABLE ledgers ADD COLUMN icon TEXT NOT NULL DEFAULT 'ic_accounts.png'"
        )


def _seed_ledger(conn: sqlite3.Connection) -> None:
    """写入默认账本（id=1），保证外键引用有效。"""
    conn.execute("INSERT OR IGNORE INTO ledgers(id, name) VALUES(1, '默认账本')")


def _seed_categories(conn: sqlite3.Connection) -> None:
    """写入默认分类（已存在则跳过）。"""
    defaults = [
        # 支出
        ("餐饮", "expense"), ("交通", "expense"), ("购物", "expense"),
        ("居住", "expense"), ("娱乐", "expense"), ("医疗", "expense"),
        ("教育", "expense"), ("转账", "expense"), ("水果", "expense"),
        ("零食", "expense"), ("服饰", "expense"), ("日用", "expense"),
        ("通讯", "expense"), ("其他支出", "expense"),
        # 收入
        ("工资", "income"), ("奖金", "income"), ("红包", "income"),
        ("退款", "income"), ("报销", "income"), ("理财", "income"),
        ("兼职", "income"), ("其他收入", "income"),
    ]
    for name, kind in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO categories(name, kind) VALUES(?, ?)",
            (name, kind),
        )


if __name__ == "__main__":
    init_db()
    print(f"✅ 数据库已初始化：{DB_PATH}")
