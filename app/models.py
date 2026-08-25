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


def delete_source(source_id: int) -> bool:
    conn = get_conn()
    try:
        # 先孤立该源的文章（source_id 可空），避免外键约束失败
        conn.execute("UPDATE articles SET source_id = NULL WHERE source_id = ?", (source_id,))
        cur = conn.execute("DELETE FROM feed_sources WHERE id = ?", (source_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ---------- 文章 articles（Feedly 模式） ----------

def add_article(
    source_id: Optional[int],
    title: str,
    url: str,
    summary: str = "",
    topic: str = "",
    publish_time: str = "",
) -> bool:
    """插入文章；url 唯一索引去重，重复返回 False。"""
    conn = get_conn()
    try:
        cur = conn.execute(
            """INSERT OR IGNORE INTO articles
               (source_id, title, url, summary, topic, publish_time)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (source_id, title, url, summary, topic, publish_time),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def add_articles(rows: Sequence[dict]) -> tuple[int, int]:
    """批量插入。rows: [{source_id, title, url, summary, topic, publish_time}]
    返回 (新增数, 重复数)。"""
    added = skipped = 0
    conn = get_conn()
    try:
        for r in rows:
            cur = conn.execute(
                """INSERT OR IGNORE INTO articles
                   (source_id, title, url, summary, topic, publish_time)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    r.get("source_id"),
                    r.get("title", ""),
                    r.get("url", ""),
                    r.get("summary", ""),
                    r.get("topic", ""),
                    r.get("publish_time", ""),
                ),
            )
            if cur.rowcount > 0:
                added += 1
            else:
                skipped += 1
        conn.commit()
        return added, skipped
    finally:
        conn.close()


def list_articles(
    date: Optional[str] = None,
    topic: Optional[str] = None,
    followed_only: bool = False,
    limit: int = 200,
) -> list[dict]:
    """文章列表，按 publish_time 倒序。

    date='YYYY-MM-DD' 只看当天；topic 只看该主题；followed_only 只看关注的主题+源。
    """
    sql = "SELECT * FROM articles WHERE 1=1"
    params: list = []
    if date:
        sql += " AND substr(publish_time, 1, 10) = ?"
        params.append(date)
    if topic:
        sql += " AND topic = ?"
        params.append(topic)
    if followed_only:
        follows = list_follows()
        topics = [f["target"] for f in follows if f["kind"] == "topic"]
        sources = [f["target"] for f in follows if f["kind"] == "source"]
        conds: list[str] = []
        if topics:
            conds.append("topic IN ({})".format(",".join("?" * len(topics))))
            params.extend(topics)
        if sources:
            conds.append("source_id IN ({})".format(",".join("?" * len(sources))))
            params.extend(sources)
        if conds:
            sql += " AND (" + " OR ".join(conds) + ")"
        else:
            return []
    sql += " ORDER BY publish_time DESC, id DESC LIMIT ?"
    params.append(limit)
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


# ---------- 关注 user_follows（topic 主题 / source 源） ----------

def add_follow(kind: str, target: str) -> bool:
    """关注一个主题或一个源。kind: topic | source；target: 主题名或源的 id 字符串。"""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO user_follows(kind, target) VALUES(?, ?)",
            (kind, target),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def list_follows() -> list[dict]:
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM user_follows ORDER BY id").fetchall()]
    finally:
        conn.close()


def delete_follow(follow_id: int) -> bool:
    conn = get_conn()
    try:
        cur = conn.execute("DELETE FROM user_follows WHERE id = ?", (follow_id,))
        conn.commit()
        return cur.rowcount > 0
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


# ---------- AI 服务 Key（管理平台可读写） ----------

def mask_key(key: str) -> str:
    """脱敏：长 Key 留前 5 后 4，中间 ***；短 Key 只留前 3。"""
    key = (key or "").strip()
    if not key:
        return ""
    if len(key) <= 12:
        return key[:3] + "***"
    return key[:5] + "***" + key[-4:]


def list_ai_keys(scope: Optional[str] = None) -> list[dict]:
    """AI Key 列表（api_key 脱敏，供管理平台/前端展示）。"""
    conn = get_conn()
    try:
        if scope:
            rows = conn.execute(
                "SELECT * FROM ai_keys WHERE scope = ? ORDER BY id", (scope,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM ai_keys ORDER BY id").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["api_key"] = mask_key(d.get("api_key"))
            out.append(d)
        return out
    finally:
        conn.close()


def get_ai_key(key_id: int) -> Optional[dict]:
    """AI Key 详情（含真实 api_key，仅限管理端/内部使用）。"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM ai_keys WHERE id = ?", (key_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_active_ai_key(provider: str = "deepseek") -> Optional[dict]:
    """取启用的 Key（供后端 AI 调用使用，含真实 api_key）。"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM ai_keys WHERE provider = ? AND status = 1 "
            "ORDER BY (scope = 'system') DESC, id LIMIT 1",
            (provider,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_ai_key(
    name: str,
    api_key: str,
    provider: str = "deepseek",
    base_url: str = "https://api.deepseek.com/v1",
    model: str = "deepseek-v4-flash",
    scope: str = "user",
    user_ref: str = "",
    status: int = 1,
    quota: float = 0,
    note: str = "",
) -> int:
    """新增 AI Key，返回新 id。"""
    conn = get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO ai_keys
               (name, provider, base_url, model, api_key, scope, user_ref,
                status, quota, note)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (name, provider, base_url, model, api_key, scope, user_ref,
             status, quota, note),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_ai_key(key_id: int, **fields) -> bool:
    """按需更新字段；Key 不存在返回 False。"""
    allowed = {"name", "provider", "base_url", "model", "api_key",
               "scope", "user_ref", "status", "quota", "note"}
    sets, params = [], []
    for k, v in fields.items():
        if k in allowed and v is not None:
            sets.append(f"{k} = ?")
            params.append(v)
    if not sets:
        return get_ai_key(key_id) is not None
    sets.append("updated_at = datetime('now','localtime')")
    params.append(key_id)
    conn = get_conn()
    try:
        cur = conn.execute(
            f"UPDATE ai_keys SET {', '.join(sets)} WHERE id = ?", params
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_ai_key(key_id: int) -> bool:
    conn = get_conn()
    try:
        cur = conn.execute("DELETE FROM ai_keys WHERE id = ?", (key_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ---------- AI 聊天会话 ai_conversations / ai_messages（经济分析 · 可回溯） ----------

def list_ai_conversations(limit: int = 100) -> list[dict]:
    """会话列表（不含消息体）：id / title / created_at / updated_at，按最近更新倒序。"""
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT id, title, created_at, updated_at FROM ai_conversations "
            "ORDER BY updated_at DESC, id DESC LIMIT ?", (limit,)
        ).fetchall()]
    finally:
        conn.close()


def get_ai_conversation(conv_id: int) -> Optional[dict]:
    """会话详情：{id, title, created_at, updated_at, messages:[{role, content}]}。"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM ai_conversations "
            "WHERE id = ?", (conv_id,),
        ).fetchone()
        if not row:
            return None
        conv = dict(row)
        msgs = conn.execute(
            "SELECT role, content FROM ai_messages "
            "WHERE conversation_id = ? ORDER BY id", (conv_id,)
        ).fetchall()
        conv["messages"] = [dict(m) for m in msgs]
        return conv
    finally:
        conn.close()


def save_ai_conversation(
    conv_id: Optional[int] = None,
    title: Optional[str] = None,
    messages: Optional[list] = None,
) -> Optional[int]:
    """保存会话快照：
    - conv_id=None → 新建会话，返回新 id
    - conv_id 存在 → 更新 title（提供时）并按 messages 重建消息（快照替换）
    - conv_id 不存在 → 返回 None
    """
    conn = get_conn()
    try:
        if conv_id is None:
            cur = conn.execute(
                "INSERT INTO ai_conversations(title) VALUES(?)", (title or "新对话",)
            )
            conv_id = cur.lastrowid
        else:
            if not conn.execute(
                "SELECT id FROM ai_conversations WHERE id = ?", (conv_id,)
            ).fetchone():
                return None
            if title:
                conn.execute(
                    "UPDATE ai_conversations SET title = ?, "
                    "updated_at = datetime('now', 'localtime') WHERE id = ?",
                    (title, conv_id),
                )
        if messages is not None:
            conn.execute(
                "DELETE FROM ai_messages WHERE conversation_id = ?", (conv_id,)
            )
            for m in messages:
                role = str((m or {}).get("role") or "user").strip()
                content = str((m or {}).get("content") or "").strip()
                if role in ("user", "ai") and content:
                    conn.execute(
                        "INSERT INTO ai_messages(conversation_id, role, content) "
                        "VALUES(?, ?, ?)", (conv_id, role, content),
                    )
            conn.execute(
                "UPDATE ai_conversations SET updated_at = datetime('now', 'localtime') "
                "WHERE id = ?", (conv_id,)
            )
        conn.commit()
        return conv_id
    finally:
        conn.close()


def delete_ai_conversation(conv_id: int) -> bool:
    """删除会话及其全部消息（显式级联，不依赖外键开关）。"""
    conn = get_conn()
    try:
        if not conn.execute(
            "SELECT id FROM ai_conversations WHERE id = ?", (conv_id,)
        ).fetchone():
            return False
        conn.execute("DELETE FROM ai_messages WHERE conversation_id = ?", (conv_id,))
        cur = conn.execute("DELETE FROM ai_conversations WHERE id = ?", (conv_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
