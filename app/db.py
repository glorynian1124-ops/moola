"""SQLite 数据库层：初始化 + 连接 + 建表。"""
import os
import sqlite3
from pathlib import Path

# 项目根目录（app/ 的上一级）
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "moola.db"

SCHEMA = """
-- 账本（预留多账本支持，MVP 单账本）
CREATE TABLE IF NOT EXISTS ledgers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT '默认账本',
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
    dedup_key TEXT UNIQUE,                  -- 去重键：md5(时间+金额+商户)，多源导入防重复
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_trans_time ON transactions(trans_time);
CREATE INDEX IF NOT EXISTS idx_trans_category ON transactions(category);

-- 预算（分类 × 月份 → 限额）
CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    month TEXT NOT NULL,                    -- 'YYYY-MM'
    limit_amount REAL NOT NULL,
    UNIQUE(category, month)
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
    """建表 + 写入默认账本和默认分类。"""
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        _seed_ledger(conn)
        _seed_categories(conn)
        conn.commit()
    finally:
        conn.close()


def _seed_ledger(conn: sqlite3.Connection) -> None:
    """写入默认账本（id=1），保证外键引用有效。"""
    conn.execute("INSERT OR IGNORE INTO ledgers(id, name) VALUES(1, '默认账本')")


def _seed_categories(conn: sqlite3.Connection) -> None:
    """写入默认分类（已存在则跳过）。"""
    defaults = [
        ("餐饮", "expense"), ("交通", "expense"), ("购物", "expense"),
        ("居住", "expense"), ("娱乐", "expense"), ("医疗", "expense"),
        ("教育", "expense"), ("转账", "expense"), ("其他支出", "expense"),
        ("收入", "income"),
    ]
    for name, kind in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO categories(name, kind) VALUES(?, ?)",
            (name, kind),
        )


if __name__ == "__main__":
    init_db()
    print(f"✅ 数据库已初始化：{DB_PATH}")
