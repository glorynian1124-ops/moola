"""数据访问层：账本 / 账单 / 类型 / 预算 / 订阅源 / 文章。"""
import hashlib
from typing import Optional, Sequence

from .db import get_conn


# ---------- 通用 ----------

def _hash_dedup(trans_time: str, amount: float, merchant: str) -> str:
    """去重键：md5(时间+金额+商户名)。多源导入同一笔消费只记一次。"""
    raw = f"{trans_time}|{amount:.2f}|{merchant}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()


# ---------- 账单 transactions ----------

def add_transaction(
    amount: float,
    category: str = "其他支出",
    merchant: str = "",
    note: str = "",
    trans_time: Optional[str] = None,
    source: str = "manual",
    ledger_id: int = 1,
) -> bool:
    """插入一笔账单，返回是否新增（False=重复已跳过）。"""
    dedup_key = _hash_dedup(trans_time or "", amount, merchant)
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT id FROM transactions WHERE dedup_key = ?", (dedup_key,)
        )
        if cur.fetchone():
            return False
        conn.execute(
            """INSERT INTO transactions
               (ledger_id, amount, category, merchant, note, trans_time, source, dedup_key)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ledger_id, amount, category, merchant, note, trans_time, source, dedup_key),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def add_many(rows: Sequence[dict]) -> tuple[int, int]:
    """批量插入。rows: [{amount, category, merchant, note, trans_time, source}]
    返回 (新增数, 重复数)。"""
    added = skipped = 0
    conn = get_conn()
    try:
        for r in rows:
            dedup_key = _hash_dedup(
                r.get("trans_time", ""), r.get("amount", 0), r.get("merchant", "")
            )
            cur = conn.execute(
                "SELECT id FROM transactions WHERE dedup_key = ?", (dedup_key,)
            )
            if cur.fetchone():
                skipped += 1
                continue
            conn.execute(
                """INSERT INTO transactions
                   (ledger_id, amount, category, merchant, note, trans_time, source, dedup_key)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r.get("ledger_id", 1),
                    r.get("amount", 0),
                    r.get("category", "其他支出"),
                    r.get("merchant", ""),
                    r.get("note", ""),
                    r.get("trans_time", ""),
                    r.get("source", "manual"),
                    dedup_key,
                ),
            )
            added += 1
        conn.commit()
        return added, skipped
    finally:
        conn.close()


def list_transactions(
    month: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 500,
) -> list[dict]:
    """查询账单。month='YYYY-MM'；倒序（最新在前）。"""
    sql = "SELECT * FROM transactions WHERE 1=1"
    params: list = []
    if month:
        sql += " AND substr(trans_time, 1, 7) = ?"
        params.append(month)
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY trans_time DESC, id DESC LIMIT ?"
    params.append(limit)
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def transaction_count() -> int:
    conn = get_conn()
    try:
        return conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    finally:
        conn.close()


# ---------- 分类 categories ----------

def list_categories() -> list[dict]:
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM categories ORDER BY id").fetchall()]
    finally:
        conn.close()


def add_category(name: str, kind: str = "expense") -> bool:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO categories(name, kind) VALUES(?, ?)", (name, kind)
        )
        conn.commit()
        return True
    finally:
        conn.close()


# ---------- 预算 budgets ----------

def set_budget(category: str, month: str, limit_amount: float) -> None:
    conn = get_conn()
    try:
        conn.execute(
            """INSERT INTO budgets(category, month, limit_amount) VALUES(?, ?, ?)
               ON CONFLICT(category, month) DO UPDATE SET limit_amount = excluded.limit_amount""",
            (category, month, limit_amount),
        )
        conn.commit()
    finally:
        conn.close()


def get_budgets(month: str) -> list[dict]:
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM budgets WHERE month = ?", (month,)).fetchall()]
    finally:
        conn.close()


# ---------- 订阅源 feed_sources（Phase 4 预留） ----------

def add_source(name: str, url: str) -> bool:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO feed_sources(name, url) VALUES(?, ?)", (name, url)
        )
        conn.commit()
        return True
    finally:
        conn.close()


def list_sources() -> list[dict]:
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM feed_sources ORDER BY id").fetchall()]
    finally:
        conn.close()
