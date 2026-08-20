"""数据访问层：账本 / 账单 / 类型 / 预算 / 订阅源 / 文章。"""
import hashlib
from typing import Optional, Sequence

from .db import get_conn


# ---------- 通用 ----------

def _hash_dedup(trans_time: str, amount: float, merchant: str) -> str:
    """去重键：md5(时间+金额+商户名)。多源导入同一笔消费只记一次。"""
    raw = f"{trans_time}|{amount:.2f}|{merchant}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()


# ---------- 账本 ledgers ----------

def list_ledgers() -> list[dict]:
    """全部账本：id / name / type / icon / created_at。"""
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM ledgers ORDER BY id").fetchall()]
    finally:
        conn.close()


def get_ledger(ledger_id: int) -> Optional[dict]:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM ledgers WHERE id = ?", (ledger_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def ledger_count() -> int:
    conn = get_conn()
    try:
        return conn.execute("SELECT COUNT(*) FROM ledgers").fetchone()[0]
    finally:
        conn.close()


def add_ledger(
    name: str, type: str = "标准账本", icon: str = "ic_accounts.png"
) -> Optional[int]:
    """新建账本，返回新账本 id。"""
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO ledgers(name, type, icon) VALUES(?, ?, ?)",
            (name, type, icon),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_ledger(
    ledger_id: int,
    *,
    name: Optional[str] = None,
    type: Optional[str] = None,
    icon: Optional[str] = None,
) -> bool:
    """更新账本可选字段（None 表示不改）；返回账本是否存在。"""
    if get_ledger(ledger_id) is None:
        return False
    sets, params = [], []
    for key, val in (("name", name), ("type", type), ("icon", icon)):
        if val is not None:
            sets.append(f"{key} = ?")
            params.append(val)
    if not sets:
        return True
    params.append(ledger_id)
    conn = get_conn()
    try:
        conn.execute(f"UPDATE ledgers SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
        return True
    finally:
        conn.close()


def delete_ledger(ledger_id: int) -> Optional[int]:
    """删除账本，并在同一事务内级联删除该账本全部账单。
    返回删除的账单数；账本不存在返回 None。"""
    conn = get_conn()
    try:
        if not conn.execute(
            "SELECT id FROM ledgers WHERE id = ?", (ledger_id,)
        ).fetchone():
            return None
        cur = conn.execute(
            "DELETE FROM transactions WHERE ledger_id = ?", (ledger_id,)
        )
        deleted = cur.rowcount
        conn.execute("DELETE FROM ledgers WHERE id = ?", (ledger_id,))
        conn.commit()
        return deleted
    finally:
        conn.close()


# ---------- 账单 transactions ----------

def add_transaction(
    amount: float,
    category: str = "其他支出",
    merchant: str = "",
    note: str = "",
    trans_time: Optional[str] = None,
    source: str = "manual",
    ledger_id: int = 1,
    raw_data: str = "",
) -> Optional[int]:
    """插入一笔账单，返回新记录 id；重复则返回 None。"""
    dedup_key = _hash_dedup(trans_time or "", amount, merchant)
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT id FROM transactions WHERE dedup_key = ?", (dedup_key,)
        )
        if cur.fetchone():
            return None
        cur = conn.execute(
            """INSERT INTO transactions
               (ledger_id, amount, category, merchant, note, trans_time, source, raw_data, dedup_key)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ledger_id, amount, category, merchant, note, trans_time, source, raw_data, dedup_key),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def add_many(rows: Sequence[dict]) -> tuple[int, int]:
    """批量插入。rows: [{amount, category, merchant, note, trans_time, source, raw_data}]
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
                   (ledger_id, amount, category, merchant, note, trans_time, source, raw_data, dedup_key)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r.get("ledger_id", 1),
                    r.get("amount", 0),
                    r.get("category", "其他支出"),
                    r.get("merchant", ""),
                    r.get("note", ""),
                    r.get("trans_time", ""),
                    r.get("source", "manual"),
                    r.get("raw_data", ""),
                    dedup_key,
                ),
            )
            added += 1
        conn.commit()
        return added, skipped
    finally:
        conn.close()


def list_transactions(
    ledger_id: Optional[int] = None,
    month: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 500,
) -> list[dict]:
    """查询账单。ledger_id=None 表示全库（向后兼容）；
    month='YYYY-MM'；倒序（最新在前）。"""
    sql = "SELECT * FROM transactions WHERE 1=1"
    params: list = []
    if ledger_id is not None:
        sql += " AND ledger_id = ?"
        params.append(ledger_id)
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


# ---------- 账单：查询 / 修改 / 删除 / 分组 / 搜索 ----------

def get_transaction(tx_id: int) -> Optional[dict]:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM transactions WHERE id = ?", (tx_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_transaction(tx_id: int, **fields) -> bool:
    """按白名单更新账单字段，返回是否存在该记录。"""
    allowed = {"amount", "category", "merchant", "note", "trans_time", "source", "ledger_id"}
    sets, params = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k} = ?")
            params.append(v)
    if not sets:
        return False
    params.append(tx_id)
    conn = get_conn()
    try:
        cur = conn.execute(
            f"UPDATE transactions SET {', '.join(sets)} WHERE id = ?", params
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_transaction(tx_id: int) -> bool:
    conn = get_conn()
    try:
        cur = conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def list_transactions_grouped(
    ledger_id: Optional[int] = None, month: Optional[str] = None
) -> dict:
    """按日期分组账单，返回前端明细页同构数据：
    {month, summary:{expense,income,balance},
     groups:[{date, spend, income, items:[{type, remark, money}]}]}
    """
    rows = list_transactions(ledger_id=ledger_id, month=month, limit=10000)
    groups: dict[str, dict] = {}
    for r in rows:
        day = r["trans_time"][:10] if r["trans_time"] else ""
        g = groups.setdefault(day, {"date": day, "spend": 0.0, "income": 0.0, "items": []})
        amt = r["amount"]
        money = amt
        merchant = r["merchant"] or ""
        note = r["note"] or ""
        remark = " · ".join(x for x in (merchant, note) if x) or "手动记账"
        g["items"].append({
            "id": r["id"],
            "type": r["category"] or "未分类",
            "remark": remark,
            "money": money,
        })
        if amt < 0:
            g["spend"] += -amt
        else:
            g["income"] += amt

    summary = {"expense": 0.0, "income": 0.0, "balance": 0.0}
    for g in groups.values():
        summary["expense"] += g["spend"]
        summary["income"] += g["income"]
    summary["balance"] = summary["income"] - summary["expense"]

    ordered = sorted(groups.values(), key=lambda g: g["date"], reverse=True)
    return {"month": month, "summary": summary, "groups": ordered}


def search_transactions(
    ledger_id: Optional[int] = None,
    q: str = "",
    mode: str = "bill",          # bill | category
    sort: str = "time",          # time | amount
    order: str = "desc",         # desc | asc
    limit: int = 200,
) -> list[dict]:
    """搜索账单。q 匹配 merchant/note/category。ledger_id=None 表示全库。"""
    sql = "SELECT * FROM transactions WHERE 1=1"
    params: list = []
    if ledger_id is not None:
        sql += " AND ledger_id = ?"
        params.append(ledger_id)
    if q:
        like = f"%{q}%"
        if mode == "category":
            sql += " AND category LIKE ?"
            params.append(like)
        else:
            sql += " AND (merchant LIKE ? OR note LIKE ? OR category LIKE ?)"
            params += [like, like, like]
    col = "trans_time" if sort == "time" else "amount"
    sql += f" ORDER BY {col} {'DESC' if order == 'desc' else 'ASC'}, id DESC LIMIT ?"
    params.append(limit)
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


# ---------- 分类规则 category_rules（AI 学习引擎） ----------

def list_rules(category: Optional[str] = None) -> list[dict]:
    conn = get_conn()
    try:
        if category:
            rows = conn.execute(
                "SELECT * FROM category_rules WHERE category = ? ORDER BY hit_count DESC",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM category_rules ORDER BY category, hit_count DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_rule(keyword: str, category: str, source: str = "user") -> bool:
    """新增分类规则；同关键词+分类已存在则忽略。"""
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT id FROM category_rules WHERE keyword = ? AND category = ?",
            (keyword, category),
        )
        if cur.fetchone():
            return False
        conn.execute(
            "INSERT INTO category_rules(keyword, category, source) VALUES(?, ?, ?)",
            (keyword, category, source),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def bump_rule(rule_id: int, delta: int = 1) -> None:
    """命中计数 +delta（学习权重）。"""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE category_rules SET hit_count = hit_count + ? WHERE id = ?",
            (delta, rule_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_rule(rule_id: int) -> bool:
    conn = get_conn()
    try:
        cur = conn.execute("DELETE FROM category_rules WHERE id = ?", (rule_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ---------- 用户画像 user_interests ----------

def list_interests(source: Optional[str] = None) -> list[dict]:
    conn = get_conn()
    try:
        if source:
            rows = conn.execute(
                "SELECT * FROM user_interests WHERE source = ? ORDER BY weight DESC",
                (source,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM user_interests ORDER BY weight DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def upsert_interest(tag: str, weight: float, source: str = "from_finance") -> None:
    """写入/更新画像标签，weight 取较大值。"""
    conn = get_conn()
    try:
        conn.execute(
            """INSERT INTO user_interests(tag, weight, source) VALUES(?, ?, ?)
               ON CONFLICT(tag, source)
               DO UPDATE SET weight = MAX(weight, excluded.weight),
                             updated_at = datetime('now', 'localtime')""",
            (tag, weight, source),
        )
        conn.commit()
    finally:
        conn.close()


# ---------- AI 分析报告 analysis_reports ----------

def add_report(
    period: str,
    kind: str,
    summary: str = "",
    insights: Optional[str] = None,
    health_score: Optional[float] = None,
    metrics: Optional[str] = None,
) -> int:
    conn = get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO analysis_reports(period, kind, summary, insights, health_score, metrics)
               VALUES(?, ?, ?, ?, ?, ?)""",
            (period, kind, summary, insights, health_score, metrics),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_reports(kind: Optional[str] = None, limit: int = 20) -> list[dict]:
    conn = get_conn()
    try:
        if kind:
            rows = conn.execute(
                "SELECT * FROM analysis_reports WHERE kind = ? ORDER BY id DESC LIMIT ?",
                (kind, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM analysis_reports ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
