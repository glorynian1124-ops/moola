"""月度消费报告：结构占比 / 趋势 / 异常提醒。"""
from collections import defaultdict
from datetime import date
from typing import Optional

from .. import models


def _latest_month_with_data(ledger_id: Optional[int] = None) -> Optional[str]:
    rows = models.list_transactions(ledger_id=ledger_id, limit=1)
    if not rows or not rows[0].get("trans_time"):
        return date.today().strftime("%Y-%m")
    return rows[0]["trans_time"][:7]


def monthly_report(
    month: Optional[str] = None, ledger_id: Optional[int] = None
) -> Optional[dict]:
    """生成月度报告。返回 None 表示该月无数据。ledger_id=None 表示全库。"""
    month = month or _latest_month_with_data(ledger_id)
    rows = models.list_transactions(ledger_id=ledger_id, month=month, limit=10000)

    total_expense = 0.0
    total_income = 0.0
    by_category: dict[str, float] = defaultdict(float)
    daily: dict[str, float] = defaultdict(float)

    for r in rows:
        amt = r["amount"]
        if amt < 0:
            total_expense += -amt
            cat = r["category"] or "未分类"
            by_category[cat] += -amt
            if r["trans_time"]:
                daily[r["trans_time"][:10]] += -amt
        else:
            total_income += amt

    if total_expense == 0 and total_income == 0:
        return None

    # 异常提醒：单日支出超过月均 2.5 倍
    anomalies = []
    if daily and total_expense > 0:
        avg_daily = total_expense / max(len(daily), 1) * 2.5
        for day, amt in sorted(daily.items(), key=lambda x: -x[1])[:3]:
            if amt > avg_daily:
                anomalies.append(f"{day} 支出 ¥{amt:,.2f}，明显高于日均水平")

    # 预算超支预警
    budgets = models.get_budgets(month)
    if budgets:
        for b in budgets:
            spent = by_category.get(b["category"], 0)
            if spent > b["limit_amount"]:
                anomalies.append(
                    f"预算超支：{b['category']} 已花 ¥{spent:,.2f}（限额 ¥{b['limit_amount']:,.2f}）"
                )

    return {
        "month": month,
        "total_expense": total_expense,
        "total_income": total_income,
        "net": total_income - total_expense,
        "by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])),
        "daily": dict(sorted(daily.items())),
        "anomalies": anomalies,
    }
