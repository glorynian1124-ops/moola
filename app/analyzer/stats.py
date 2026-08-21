"""统计聚合：趋势（周/月/年）+ 分类占比 + 日历每日收支。"""
import calendar
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from .. import models


def _range_rows(
    start_date: str, end_date: str, ledger_id: Optional[int] = None
) -> list[dict]:
    """按日期区间加载交易（trans_time 介于 start 与 end 当天之间）。
    ledger_id=None 表示全库（向后兼容）。"""
    from ..db import get_conn

    sql = "SELECT * FROM transactions WHERE trans_time >= ? AND trans_time <= ?"
    params: list = [start_date, end_date + " 23:59:59"]
    if ledger_id is not None:
        sql += " AND ledger_id = ?"
        params.append(ledger_id)
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _labels_for(period: str, end_d: date) -> list[str]:
    """返回时间桶标签列表。"""
    if period == "week":
        monday = end_d - timedelta(days=end_d.weekday())
        return [(monday + timedelta(days=i)).isoformat() for i in range(7)]
    if period == "month":
        dim = calendar.monthrange(end_d.year, end_d.month)[1]
        return [date(end_d.year, end_d.month, d).isoformat() for d in range(1, dim + 1)]
    # year
    return [date(end_d.year, m, 1).strftime("%Y-%m") for m in range(1, 13)]


def trend(
    period: str = "week",
    cat: str = "expense",
    end: Optional[str] = None,
    ledger_id: Optional[int] = None,
) -> dict:
    """趋势聚合。period: week|month|year；cat: expense|income。
    ledger_id=None 表示全库。
    返回 {period, cat, buckets:[{label,value}], max}。"""
    end_d = date.fromisoformat(end) if end else date.today()
    labels = _labels_for(period, end_d)
    if period == "year":
        start, end_day = f"{end_d.year}-01-01", f"{end_d.year}-12-31"
    else:
        start, end_day = labels[0], labels[-1]

    sign = -1 if cat == "expense" else 1
    sums: dict[str, float] = defaultdict(float)
    for r in _range_rows(start, end_day, ledger_id):
        if r["amount"] * sign <= 0:   # 只看目标方向
            continue
        key = r["trans_time"][:7] if period == "year" else r["trans_time"][:10]
        sums[key] += abs(r["amount"])

    buckets = [{"label": l, "value": round(sums.get(l, 0), 2)} for l in labels]
    return {
        "period": period,
        "cat": cat,
        "buckets": buckets,
        "max": max([b["value"] for b in buckets] or [0]),
    }


def category_share(
    month: Optional[str] = None,
    cat: str = "expense",
    ledger_id: Optional[int] = None,
) -> list[dict]:
    """分类占比（环形图）。返回 [{name, value}]，按金额降序。
    ledger_id=None 表示全库。"""
    rows = models.list_transactions(ledger_id=ledger_id, month=month, limit=10000)
    sign = -1 if cat == "expense" else 1
    m: dict[str, float] = defaultdict(float)
    for r in rows:
        if r["amount"] * sign <= 0:
            continue
        m[r["category"] or "未分类"] += abs(r["amount"])
    return [{"name": k, "value": round(v, 2)} for k, v in sorted(m.items(), key=lambda x: -x[1])]


def daily_calendar(
    month: Optional[str] = None, ledger_id: Optional[int] = None
) -> dict:
    """日历页：某月每日收支。返回 {month, days:[{date,expense,income,count}]}。
    ledger_id=None 表示全库。"""
    rows = models.list_transactions(ledger_id=ledger_id, month=month, limit=10000)
    days: dict[str, dict] = defaultdict(lambda: {"date": "", "expense": 0.0, "income": 0.0, "count": 0})
    for r in rows:
        d = r["trans_time"][:10]
        day = days[d]
        day["date"] = d
        if r["amount"] < 0:
            day["expense"] += -r["amount"]
        else:
            day["income"] += r["amount"]
        day["count"] += 1
    ordered = sorted((dict(v) for v in days.values()), key=lambda x: x["date"])
    for d in ordered:
        d["expense"] = round(d["expense"], 2)
        d["income"] = round(d["income"], 2)
    return {"month": month, "days": ordered}
